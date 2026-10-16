from datetime import timedelta

from django.apps import apps
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from usuarios.models import Usuario

from .forms import CrearUsuarioForm
from .mixins import PanelMixin

USUARIOS_POR_PAGINA = 20
FILAS_POR_PAGINA = 25

# Columnas que el explorador de la base de datos nunca muestra.
COLUMNAS_SENSIBLES = {'password', 'session_key', 'session_data'}


class _NoQuedanSuperusuarios(Exception):
    """Se lanza dentro de una transacción para deshacerla."""


def _hay_superusuario_activo():
    return Usuario.objects.filter(is_superuser=True, is_active=True).exists()


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
class ResumenView(PanelMixin, TemplateView):
    template_name = 'panel/resumen.html'
    seccion = 'resumen'
    subtitulo = 'Gestiona cuentas y consulta la base de datos.'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        hace_7_dias = timezone.now() - timedelta(days=7)
        contexto.update(
            total=Usuario.objects.count(),
            activos=Usuario.objects.filter(is_active=True).count(),
            suspendidos=Usuario.objects.filter(is_active=False).count(),
            superusuarios=Usuario.objects.filter(is_superuser=True).count(),
            nuevos_7_dias=Usuario.objects.filter(fecha_registro__gte=hace_7_dias).count(),
            puntos_totales=Usuario.objects.aggregate(t=Sum('puntos'))['t'] or 0,
            recientes=Usuario.objects.order_by('-fecha_registro')[:5],
            motor=connection.vendor,
        )
        return contexto


# ---------------------------------------------------------------------------
# Usuarios: listado
# ---------------------------------------------------------------------------
class UsuariosView(PanelMixin, TemplateView):
    template_name = 'panel/usuarios.html'
    seccion = 'usuarios'
    titulo = 'Usuarios'
    subtitulo = 'Crea, suspende o elimina cuentas.'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '')
        rol = self.request.GET.get('rol', '')

        usuarios = Usuario.objects.all()
        if q:
            usuarios = usuarios.filter(Q(correo__icontains=q) | Q(nombre__icontains=q))
        if estado == 'activos':
            usuarios = usuarios.filter(is_active=True)
        elif estado == 'suspendidos':
            usuarios = usuarios.filter(is_active=False)
        if rol == 'superusuarios':
            usuarios = usuarios.filter(is_superuser=True)
        elif rol == 'normales':
            usuarios = usuarios.filter(is_superuser=False)

        pagina = Paginator(usuarios.order_by('-fecha_registro', '-pk'), USUARIOS_POR_PAGINA)
        pagina = pagina.get_page(self.request.GET.get('page'))

        # Para conservar los filtros al cambiar de página
        parametros = self.request.GET.copy()
        parametros.pop('page', None)
        contexto.update(pagina=pagina, q=q, estado=estado, rol=rol,
                        filtros_url=parametros.urlencode())
        return contexto


# ---------------------------------------------------------------------------
# Usuarios: crear
# ---------------------------------------------------------------------------
class CrearUsuarioView(PanelMixin, FormView):
    template_name = 'panel/usuario_crear.html'
    form_class = CrearUsuarioForm
    success_url = reverse_lazy('panel:usuarios')
    seccion = 'usuarios'
    titulo = 'Crear cuenta'
    icono = 'fa-user-plus'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['actor'] = self.request.user
        return kwargs

    def form_valid(self, form):
        usuario = form.save()
        tipo = 'superusuario' if usuario.is_superuser else 'usuario'
        messages.success(self.request, f'Se creó la cuenta de {tipo} {usuario.correo}.')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Usuarios: suspender / reactivar / eliminar
# ---------------------------------------------------------------------------
class _AccionSobreUsuarioView(PanelMixin, View):
    """Base de las acciones que modifican a otra cuenta. Solo POST y nunca sobre uno mismo."""
    http_method_names = ['post']

    def objetivo(self, pk):
        return get_object_or_404(Usuario, pk=pk)

    def rechazar_si_es_uno_mismo(self, request, objetivo, accion):
        if objetivo.pk == request.user.pk:
            messages.error(request, f'No puedes {accion} tu propia cuenta.')
            return redirect('panel:usuarios')
        return None


class SuspenderUsuarioView(_AccionSobreUsuarioView):
    def post(self, request, pk):
        objetivo = self.objetivo(pk)
        rechazo = self.rechazar_si_es_uno_mismo(request, objetivo, 'suspender')
        if rechazo:
            return rechazo
        try:
            with transaction.atomic():
                objetivo.is_active = False
                objetivo.save(update_fields=['is_active'])
                if not _hay_superusuario_activo():
                    raise _NoQuedanSuperusuarios
        except _NoQuedanSuperusuarios:
            messages.error(request, 'No se puede: debe quedar al menos un superusuario activo.')
            return redirect('panel:usuarios')
        messages.success(request, f'La cuenta {objetivo.correo} fue suspendida. Su sesión se cerró.')
        return redirect('panel:usuarios')


class ReactivarUsuarioView(_AccionSobreUsuarioView):
    def post(self, request, pk):
        objetivo = self.objetivo(pk)
        objetivo.is_active = True
        objetivo.save(update_fields=['is_active'])
        messages.success(request, f'La cuenta {objetivo.correo} fue reactivada.')
        return redirect('panel:usuarios')


class EliminarUsuarioView(PanelMixin, TemplateView):
    """GET: pantalla de confirmación. POST: elimina de forma definitiva."""
    template_name = 'panel/usuario_eliminar.html'
    seccion = 'usuarios'
    titulo = 'Eliminar cuenta'
    icono = 'fa-user-times'
    http_method_names = ['get', 'post']

    def get_objetivo(self):
        return get_object_or_404(Usuario, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['objetivo'] = self.get_objetivo()
        return contexto

    def get(self, request, *args, **kwargs):
        objetivo = self.get_objetivo()
        if objetivo.pk == request.user.pk:
            messages.error(request, 'No puedes eliminar tu propia cuenta.')
            return redirect('panel:usuarios')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        objetivo = self.get_objetivo()
        if objetivo.pk == request.user.pk:
            messages.error(request, 'No puedes eliminar tu propia cuenta.')
            return redirect('panel:usuarios')

        # Eliminar a un superusuario exige la contraseña de quien lo hace.
        if objetivo.is_superuser and not request.user.check_password(request.POST.get('password_admin', '')):
            contexto = self.get_context_data(**kwargs)
            contexto['error_password'] = 'Tu contraseña no es correcta.'
            return self.render_to_response(contexto)

        correo = objetivo.correo
        try:
            with transaction.atomic():
                objetivo.delete()
                if not _hay_superusuario_activo():
                    raise _NoQuedanSuperusuarios
        except _NoQuedanSuperusuarios:
            messages.error(request, 'No se puede: debe quedar al menos un superusuario activo.')
            return redirect('panel:usuarios')
        messages.success(request, f'La cuenta {correo} fue eliminada de forma definitiva.')
        return redirect('panel:usuarios')


# ---------------------------------------------------------------------------
# Base de datos (solo lectura)
# ---------------------------------------------------------------------------
def _modelo_o_404(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        raise Http404


class BaseDatosView(PanelMixin, TemplateView):
    template_name = 'panel/base_datos.html'
    seccion = 'base_datos'
    titulo = 'Base de datos'
    icono = 'fa-database'
    subtitulo = 'Vista de solo lectura de las tablas del sitio.'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        tablas = []
        for modelo in sorted(apps.get_models(), key=lambda m: m._meta.db_table):
            tablas.append({
                'tabla': modelo._meta.db_table,
                'app': modelo._meta.app_label,
                'modelo': modelo._meta.model_name,
                'filas': modelo._default_manager.count(),
                'columnas': len(modelo._meta.concrete_fields),
            })
        contexto.update(tablas=tablas, motor=connection.vendor)
        return contexto


class TablaView(PanelMixin, TemplateView):
    template_name = 'panel/tabla.html'
    seccion = 'base_datos'
    icono = 'fa-table'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        modelo = _modelo_o_404(self.kwargs['app_label'], self.kwargs['model_name'])
        campos = list(modelo._meta.concrete_fields)

        pagina = Paginator(modelo._default_manager.order_by('pk'), FILAS_POR_PAGINA)
        pagina = pagina.get_page(self.request.GET.get('page'))

        filas = []
        for obj in pagina:
            # attname (p. ej. "usuario_id") evita consultas extra por cada clave foránea.
            filas.append([
                '••••••••' if campo.name in COLUMNAS_SENSIBLES else getattr(obj, campo.attname)
                for campo in campos
            ])

        contexto.update(
            tabla=modelo._meta.db_table,
            columnas=[campo.attname for campo in campos],
            filas=filas,
            pagina=pagina,
            page_titulo=modelo._meta.db_table,
            hero_subtitulo='Solo lectura. Las contraseñas y claves de sesión están ocultas.',
        )
        return contexto
