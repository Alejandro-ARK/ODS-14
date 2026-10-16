from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.shortcuts import redirect, resolve_url
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import FormView, UpdateView

from core.mixins import HeroMixin

from .forms import LoginForm, PerfilForm, RegistroForm

# Nadie debería ganar más de 100 puntos por una sola actividad.
MAX_PUNTOS_POR_ACTIVIDAD = 100


class _SoloAnonimosMixin:
    """Si ya hay sesión iniciada, login y registro mandan al inicio."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:inicio')
        return super().dispatch(request, *args, **kwargs)


class LoginView(_SoloAnonimosMixin, FormView):
    template_name = 'usuarios/login.html'
    form_class = LoginForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        # Respeta ?next=/ruta/ (lo añade @login_required), solo si es del mismo sitio.
        destino = self.request.POST.get('next') or self.request.GET.get('next')
        if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure(),
        ):
            return destino
        return resolve_url('core:inicio')

    def form_valid(self, form):
        login(self.request, form.usuario)
        return redirect(self.get_success_url())


class RegistroView(_SoloAnonimosMixin, FormView):
    template_name = 'usuarios/registro.html'
    form_class = RegistroForm

    def form_valid(self, form):
        usuario = form.save()
        login(self.request, usuario)   # el registro inicia sesión automáticamente
        return redirect('core:inicio')


class PerfilView(LoginRequiredMixin, HeroMixin, SuccessMessageMixin, UpdateView):
    template_name = 'usuarios/perfil.html'
    form_class = PerfilForm
    success_url = reverse_lazy('usuarios:perfil')
    success_message = '¡Tu nombre de perfil se actualizó correctamente!'

    titulo = 'Mi perfil'
    icono = 'fa-user-circle'

    def get_object(self, queryset=None):
        return self.request.user


@require_POST
def guardar_puntos(request):
    """Endpoint AJAX: suma puntos al usuario con sesión y recalcula su nivel."""
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'No has iniciado sesión.'}, status=401)

    try:
        puntos = int(request.POST.get('puntos', 0))
    except (TypeError, ValueError):
        puntos = 0
    puntos = max(0, min(MAX_PUNTOS_POR_ACTIVIDAD, puntos))

    if puntos <= 0:
        return JsonResponse({'ok': False, 'error': 'Puntos inválidos.'}, status=400)

    request.user.sumar_puntos(puntos)
    return JsonResponse({
        'ok': True,
        'puntos': request.user.puntos,                       # total ganado (de él sale el nivel)
        'disponibles': request.user.puntos_disponibles,      # lo que se puede gastar en la tienda
        'nivel': request.user.nivel,
    })
