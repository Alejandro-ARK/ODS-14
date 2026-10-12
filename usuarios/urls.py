from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('registro/', views.RegistroView.as_view(), name='registro'),
    path('logout/', LogoutView.as_view(), name='logout'),          # solo acepta POST
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('guardar-puntos/', views.guardar_puntos, name='guardar_puntos'),
]
