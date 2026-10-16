from django.urls import path

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.ResumenView.as_view(), name='resumen'),

    path('usuarios/', views.UsuariosView.as_view(), name='usuarios'),
    path('usuarios/nuevo/', views.CrearUsuarioView.as_view(), name='usuario_crear'),
    path('usuarios/<int:pk>/suspender/', views.SuspenderUsuarioView.as_view(), name='usuario_suspender'),
    path('usuarios/<int:pk>/reactivar/', views.ReactivarUsuarioView.as_view(), name='usuario_reactivar'),
    path('usuarios/<int:pk>/eliminar/', views.EliminarUsuarioView.as_view(), name='usuario_eliminar'),

    path('base-de-datos/', views.BaseDatosView.as_view(), name='base_datos'),
    path('base-de-datos/<str:app_label>/<str:model_name>/', views.TablaView.as_view(), name='tabla'),
]
