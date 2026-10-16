from django.urls import path

from . import views

app_name = 'tienda'

urlpatterns = [
    path('', views.TiendaView.as_view(), name='tienda'),
    path('comprar/<int:pk>/', views.ComprarView.as_view(), name='comprar'),
    path('equipar/<int:pk>/', views.EquiparView.as_view(), name='equipar'),
]
