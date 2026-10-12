from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.InicioView.as_view(), name='inicio'),
    path('aprende/', views.AprendeView.as_view(), name='aprende'),
    path('juega/', views.JuegaView.as_view(), name='juega'),
    path('quiz/', views.QuizView.as_view(), name='quiz'),
    path('mares/', views.MaresView.as_view(), name='mares'),
    path('actua/', views.ActuaView.as_view(), name='actua'),
]
