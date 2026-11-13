from django.contrib import admin

from .models import Opcion, Participante, Pregunta, RespuestaReto, Sala, SalaPregunta


class OpcionInline(admin.TabularInline):
    model = Opcion
    extra = 0
    min_num = 2
    max_num = 4


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    """Banco de preguntas del reto: aquí se agregan, editan o desactivan."""
    list_display = ('enunciado', 'tema', 'activa')
    list_editable = ('activa',)
    list_filter = ('tema', 'activa')
    search_fields = ('enunciado',)
    inlines = [OpcionInline]


class SalaPreguntaInline(admin.TabularInline):
    model = SalaPregunta
    extra = 0
    raw_id_fields = ('pregunta',)


class ParticipanteInline(admin.TabularInline):
    model = Participante
    extra = 0
    raw_id_fields = ('usuario',)
    readonly_fields = ('unido_en',)


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ('pin', 'docente', 'estado', 'segundos', 'indice_actual', 'creada_en')
    list_filter = ('estado',)
    search_fields = ('pin', 'docente__correo')
    raw_id_fields = ('docente',)
    inlines = [SalaPreguntaInline, ParticipanteInline]


@admin.register(RespuestaReto)
class RespuestaRetoAdmin(admin.ModelAdmin):
    list_display = ('participante', 'pregunta', 'correcta', 'tiempo_ms', 'puntos')
    list_filter = ('correcta',)
    raw_id_fields = ('participante', 'pregunta', 'opcion')
