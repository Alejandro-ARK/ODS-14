"""
Reto en vivo: partidas tipo concurso que un docente dirige y los estudiantes juegan
al mismo tiempo desde su celular (documento técnico, sección 5).
"""
from django.conf import settings
from django.db import models

GRUPO_DOCENTES = 'Docentes'

MIN_PREGUNTAS, MAX_PREGUNTAS = 5, 15
MIN_SEGUNDOS, MAX_SEGUNDOS = 10, 30


def es_docente(usuario):
    """RF-01: solo el grupo «Docentes» crea salas (los superusuarios también pueden)."""
    if not usuario.is_authenticated:
        return False
    return usuario.is_superuser or usuario.groups.filter(name=GRUPO_DOCENTES).exists()


class Pregunta(models.Model):
    """Banco de preguntas del reto (las del quiz de /quiz/ y más, migradas a la base)."""
    enunciado = models.CharField(max_length=300)
    tema = models.CharField(max_length=40)
    activa = models.BooleanField(default=True, help_text='Solo las activas se usan al crear salas.')

    class Meta:
        verbose_name = 'pregunta'
        verbose_name_plural = 'preguntas'
        ordering = ['tema', 'id']

    def __str__(self):
        return self.enunciado


class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=150)
    correcta = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'opción'
        verbose_name_plural = 'opciones'

    def __str__(self):
        return self.texto


class Sala(models.Model):
    ESPERA, PREGUNTA, RESULTADOS, FINALIZADA = 'espera', 'pregunta', 'resultados', 'finalizada'
    ESTADOS = [
        (ESPERA, 'En espera'),
        (PREGUNTA, 'Pregunta abierta'),
        (RESULTADOS, 'Mostrando resultados'),
        (FINALIZADA, 'Finalizada'),
    ]
    ABIERTAS = [ESPERA, PREGUNTA, RESULTADOS]   # estados en los que se puede entrar

    docente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='salas_reto')
    pin = models.CharField(max_length=6, unique=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESPERA)
    segundos = models.PositiveSmallIntegerField(default=20)
    preguntas = models.ManyToManyField(Pregunta, through='SalaPregunta')
    indice_actual = models.SmallIntegerField(default=-1)
    iniciada_en = models.DateTimeField(null=True, blank=True)   # inicio de la pregunta actual
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'sala'
        verbose_name_plural = 'salas'
        ordering = ['-creada_en']

    def __str__(self):
        return f'Sala {self.pin} ({self.get_estado_display()})'

    @property
    def total_preguntas(self):
        return self.salapregunta_set.count()


class SalaPregunta(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.PROTECT)
    orden = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['orden']
        constraints = [models.UniqueConstraint(fields=['sala', 'orden'], name='orden_unico')]


class Participante(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='participantes')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participaciones_reto')
    puntaje = models.PositiveIntegerField(default=0)
    # RF-09: puntos (0-100) que se sumaron a la cuenta al finalizar la partida.
    puntos_cuenta = models.PositiveSmallIntegerField(default=0)
    unido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'participante'
        verbose_name_plural = 'participantes'
        constraints = [models.UniqueConstraint(fields=['sala', 'usuario'], name='participante_unico')]

    def __str__(self):
        return f'{self.usuario} en {self.sala.pin}'


class RespuestaReto(models.Model):
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(Pregunta, on_delete=models.PROTECT)
    opcion = models.ForeignKey(Opcion, on_delete=models.PROTECT)
    correcta = models.BooleanField()
    tiempo_ms = models.PositiveIntegerField()
    puntos = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'respuesta del reto'
        verbose_name_plural = 'respuestas del reto'
        constraints = [models.UniqueConstraint(fields=['participante', 'pregunta'], name='una_respuesta')]
