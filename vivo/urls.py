from django.urls import path

from . import views

app_name = 'vivo'

urlpatterns = [
    path('', views.InicioVivoView.as_view(), name='inicio'),
    path('unirse/', views.unirse, name='unirse'),              # destino del QR: ?t=<token firmado>
    path('unirse/pin/', views.unirse_pin, name='unirse_pin'),  # alternativa: PIN de 6 dígitos
    path('sala/<str:pin>/', views.SalaView.as_view(), name='sala'),
    path('sala/<str:pin>/qr/', views.qr_sala, name='qr'),
    path('sala/<str:pin>/eliminar/', views.eliminar_sala, name='eliminar'),
]
