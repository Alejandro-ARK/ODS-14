from django.contrib.auth.mixins import AccessMixin
from django.http import Http404

from core.mixins import HeroMixin


class SoloSuperusuarioMixin(AccessMixin):
    """
    Acceso exclusivo para superusuarios.

    - Sin sesión: se envía al login (y vuelve al panel después de entrar).
    - Con sesión pero sin ser superusuario: 404, para no revelar que el panel existe.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_active and request.user.is_superuser):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class PanelMixin(SoloSuperusuarioMixin, HeroMixin):
    """Base de todas las vistas del panel: acceso restringido + franja de título."""
    titulo = 'Panel de administración'
    icono = 'fa-user-shield'
    seccion = ''   # resalta la pestaña activa en la navegación del panel

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['seccion'] = self.seccion
        return contexto
