from django.urls import path

from .consumers import RetoConsumer

websocket_urlpatterns = [
    path('ws/vivo/<str:pin>/', RetoConsumer.as_asgi()),
]
