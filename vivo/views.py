"""
Vistas HTTP del reto en vivo: crear sala, QR dinámico, unirse (por QR o PIN) y la pantalla
de juego. Lo que pasa durante la partida viaja por WebSocket (ver consumers.py).
"""
import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.mixins import HeroMixin

from . import servicios
from .forms import CrearSalaForm, PinForm
from .models import Participante, Pregunta, Sala, es_docente

SAL_QR = 'reto-qr'
QR_VIGENCIA = 10 * 60        # RF-03: el token expira a los 10 minutos…
QR_REFRESCO = 5 * 60         # …y la pantalla del docente lo renueva cada 5

_CONTEXTO_VENCIDO = {'page_titulo': 'Reto en vivo', 'hero_icono': 'fa-broadcast-tower'}


class InicioVivoView(LoginRequiredMixin, HeroMixin, TemplateView):
    """«Reto en vivo»: el docente crea salas; el estudiante entra con el PIN."""
    template_name = 'vivo/inicio.html'
    titulo = 'Reto en vivo'
    icono = 'fa-broadcast-tower'
    subtitulo = 'Compite con tu clase en tiempo real: misma pregunta, mismo reloj, ranking en vivo.'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        docente = es_docente(self.request.user)
        contexto.update(
            es_docente=docente,
            pin_form=kwargs.get('pin_form') or PinForm(),
            sala_form=kwargs.get('sala_form') or CrearSalaForm(),
            banco=Pregunta.objects.filter(activa=True).count(),
            mis_participaciones=(Participante.objects.filter(usuario=self.request.user)
                                 .select_related('sala').order_by('-unido_en')[:5]),
        )
        if docente:
            contexto['mis_salas'] = Sala.objects.filter(docente=self.request.user)[:10]
        return contexto

    def post(self, request, *args, **kwargs):
        """Crear una sala (solo docentes)."""
        if not es_docente(request.user):
            raise Http404
        form = CrearSalaForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(sala_form=form))
        sala = servicios.crear_sala(request.user, form.cleaned_data['cantidad'], form.cleaned_data['segundos'])
        messages.success(request, f'Sala {sala.pin} creada. Proyecta esta pantalla para que tu clase escanee el QR.')
        return redirect('vivo:sala', pin=sala.pin)


@login_required
@never_cache
def qr_sala(request, pin):
    """RF-03: QR (SVG) con un token firmado que incluye la hora en que se generó."""
    sala = get_object_or_404(Sala, pin=pin, docente=request.user)
    token = signing.dumps({'s': sala.id}, salt=SAL_QR)
    url = request.build_absolute_uri(f"{reverse('vivo:unirse')}?t={token}")
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12)
    return HttpResponse(img.to_string(), content_type='image/svg+xml')


@login_required
def unirse(request):
    """Destino del QR: valida la firma y la vigencia del token y deja al estudiante en la sala."""
    try:
        datos = signing.loads(request.GET['t'], salt=SAL_QR, max_age=QR_VIGENCIA)
    except (signing.BadSignature, KeyError):   # SignatureExpired hereda de BadSignature
        return render(request, 'vivo/qr_vencido.html', _CONTEXTO_VENCIDO, status=400)
    sala = Sala.objects.filter(id=datos.get('s'), estado__in=Sala.ABIERTAS).first()
    if sala is None:
        return render(request, 'vivo/qr_vencido.html', {**_CONTEXTO_VENCIDO, 'cerrada': True}, status=400)
    return _entrar(request, sala)


@login_required
@require_POST
def unirse_pin(request):
    """Alternativa al QR: el PIN de 6 dígitos."""
    form = PinForm(request.POST)
    sala = None
    if form.is_valid():
        sala = Sala.objects.filter(pin=form.cleaned_data['pin'], estado__in=Sala.ABIERTAS).first()
    if sala is None:
        messages.error(request, 'No hay ninguna sala abierta con ese PIN.')
        return redirect('vivo:inicio')
    return _entrar(request, sala)


def _entrar(request, sala):
    if sala.docente_id != request.user.pk:
        Participante.objects.get_or_create(sala=sala, usuario=request.user)
    return redirect('vivo:sala', pin=sala.pin)


class SalaView(LoginRequiredMixin, TemplateView):
    """Pantalla del juego: la del docente se proyecta; la del estudiante son 4 botones grandes."""

    def get_template_names(self):
        return ['vivo/docente.html' if self.es_docente else 'vivo/estudiante.html']

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.sala = get_object_or_404(Sala, pin=kwargs['pin'])
        self.es_docente = self.sala.docente_id == request.user.pk
        if not self.es_docente and not Participante.objects.filter(sala=self.sala, usuario=request.user).exists():
            messages.info(request, 'Para entrar a esa sala escanea el QR o escribe su PIN.')
            return redirect('vivo:inicio')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(sala=self.sala, qr_refresco_ms=QR_REFRESCO * 1000,
                        page_titulo=f'Reto en vivo · Sala {self.sala.pin}', hero_icono='fa-broadcast-tower')
        return contexto


@login_required
@require_POST
def eliminar_sala(request, pin):
    sala = get_object_or_404(Sala, pin=pin, docente=request.user)
    sala.delete()
    messages.success(request, f'Se eliminó la sala {pin}.')
    return redirect('vivo:inicio')
