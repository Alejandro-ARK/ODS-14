from django.views.generic import TemplateView

from .mixins import HeroMixin


class PaginaView(HeroMixin, TemplateView):
    """Página estática con su franja de título."""


class InicioView(PaginaView):
    template_name = 'core/index.html'
    titulo = '¡Bienvenido/a a Misión Océano! 🌊'
    subtitulo = 'Un espacio educativo para aprender, jugar y actuar en favor del ODS 14: Vida Submarina.'
    hero_grande = True


class AprendeView(PaginaView):
    template_name = 'core/aprende.html'
    titulo = 'Aprende'
    icono = 'fa-book-open'
    subtitulo = 'Todo lo que necesitas saber sobre el ODS 14 y la vida submarina.'


class JuegaView(PaginaView):
    template_name = 'core/juega.html'
    titulo = 'Juega'
    icono = 'fa-gamepad'
    subtitulo = 'Diviértete mientras aprendes a cuidar el océano.'


class QuizView(PaginaView):
    template_name = 'core/quiz.html'
    titulo = 'Demuestra lo que sabes'
    icono = 'fa-brain'
    subtitulo = 'Responde el quiz sobre el ODS 14 y la vida marina, y gana puntos.'


class MaresView(PaginaView):
    template_name = 'core/mares.html'
    titulo = 'Conoce nuestros mares'
    icono = 'fa-water'
    subtitulo = 'Colombia: un país con costas en dos océanos distintos.'


class ActuaView(PaginaView):
    template_name = 'core/actua.html'
    titulo = 'Actúa'
    icono = 'fa-leaf'
    subtitulo = 'Pequeñas acciones, gran impacto para la vida submarina.'
