"""
Punto de entrada ASGI: sirve las páginas normales (HTTP) y los WebSockets del reto en vivo.

En producción lo ejecuta Daphne:  daphne -b 0.0.0.0 -p $PORT config.asgi:application
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django debe inicializarse ANTES de importar consumidores que usan modelos.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from vivo.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    # AuthMiddlewareStack lee la sesión de Django (scope['user']);
    # AllowedHostsOriginValidator rechaza conexiones desde otros dominios.
    'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
})
