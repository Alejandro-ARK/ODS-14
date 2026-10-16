from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('panel/', include('panel.urls')),   # panel de superusuarios (usuarios + base de datos)
    path('tienda/', include('tienda.urls')), # tienda de avatares
    path('', include('usuarios.urls')),   # login, registro, perfil, logout, guardar-puntos
    path('', include('core.urls')),       # páginas educativas
]
