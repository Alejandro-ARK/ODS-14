from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),   # login, registro, perfil, logout, guardar-puntos
    path('', include('core.urls')),       # páginas educativas
]
