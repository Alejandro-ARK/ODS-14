"""
Lógica del reto en vivo. Todo lo que decide puntos, tiempos y estados ocurre aquí, en el
servidor (RF-05, RF-06): el cliente solo muestra lo que recibe.

Las funciones son síncronas para poder probarlas fácilmente; el consumidor de WebSocket
las envuelve con `database_sync_to_async`.
"""
import random
import secrets

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Opcion, Participante, Pregunta, RespuestaReto, Sala, SalaPregunta

PUNTOS_MAXIMOS = 1000           # por pregunta
PUNTOS_CUENTA_MAXIMOS = 100     # RF-09: lo máximo que una partida suma a la cuenta
TOP = 5


# ---------------------------------------------------------------------------
# Crear sala
# ---------------------------------------------------------------------------
def generar_pin():
    """PIN de 6 dígitos que no esté en uso por otra sala abierta."""
    for _ in range(50):
        pin = f'{secrets.randbelow(10 ** 6):06d}'
        if not Sala.objects.filter(pin=pin).exists():
            return pin
    raise RuntimeError('No se pudo generar un PIN libre.')


def crear_sala(docente, cantidad, segundos):
    """RF-02: sala con `cantidad` preguntas al azar del banco y `segundos` por pregunta."""
    ids = list(Pregunta.objects.filter(activa=True).values_list('id', flat=True))
    if len(ids) < cantidad:
        raise ValueError(f'El banco solo tiene {len(ids)} preguntas activas.')
    elegidas = random.sample(ids, cantidad)
    with transaction.atomic():
        sala = Sala.objects.create(docente=docente, pin=generar_pin(), segundos=segundos)
        SalaPregunta.objects.bulk_create(
            SalaPregunta(sala=sala, pregunta_id=pid, orden=i) for i, pid in enumerate(elegidas))
    return sala


# ---------------------------------------------------------------------------
# Consultas de apoyo
# ---------------------------------------------------------------------------
def rol_en_sala(pin, usuario):
    """'docente', 'estudiante' o None (sin permiso para conectarse)."""
    if not usuario.is_authenticated:
        return None
    sala = Sala.objects.filter(pin=pin).first()
    if sala is None:
        return None
    if sala.docente_id == usuario.pk:
        return 'docente'
    if Participante.objects.filter(sala=sala, usuario=usuario).exists():
        return 'estudiante'
    return None


def lista_jugadores(pin):
    return list(Participante.objects.filter(sala__pin=pin)
                .order_by('unido_en').values_list('usuario__nombre', flat=True))


def _pregunta_en(sala, indice):
    return SalaPregunta.objects.select_related('pregunta').get(sala=sala, orden=indice).pregunta


def _ms_transcurridos(sala):
    return int((timezone.now() - sala.iniciada_en).total_seconds() * 1000)


def _datos_pregunta(sala, pregunta):
    """La pregunta SIN la respuesta correcta (RF-05). Las opciones van en orden aleatorio."""
    opciones = [{'id': o.id, 'texto': o.texto} for o in pregunta.opciones.all()]
    random.shuffle(opciones)
    restante = max(0, sala.segundos * 1000 - _ms_transcurridos(sala))
    return {
        'tipo': 'pregunta',
        'indice': sala.indice_actual,
        'total': sala.total_preguntas,
        'segundos': sala.segundos,
        'restante_ms': restante,
        'pregunta': {'id': pregunta.id, 'enunciado': pregunta.enunciado,
                     'tema': pregunta.tema, 'opciones': opciones},
    }


def _ranking(sala, limite=TOP):
    """Top de la sala con el avatar personalizado de cada jugador (URLs de sus capas PNG)."""
    return [
        {'nombre': p.usuario.nombre, 'puntaje': p.puntaje, 'avatar': p.usuario.capas_avatar()}
        for p in sala.participantes.select_related('usuario').order_by('-puntaje', 'unido_en')[:limite]
    ]


def _conteo(sala, pregunta_id):
    return {
        'tipo': 'conteo',
        'respondidas': RespuestaReto.objects.filter(participante__sala=sala, pregunta_id=pregunta_id).count(),
        'jugadores': sala.participantes.count(),
    }


def _resultados(sala):
    """Lo que se difunde al cerrar una pregunta (RF-07)."""
    pregunta = _pregunta_en(sala, sala.indice_actual)
    correcta = pregunta.opciones.filter(correcta=True).first()
    respuestas = RespuestaReto.objects.filter(participante__sala=sala, pregunta=pregunta)
    return {
        'tipo': 'resultados',
        'indice': sala.indice_actual,
        'total': sala.total_preguntas,
        'ultima': sala.indice_actual + 1 >= sala.total_preguntas,
        'pregunta': {'id': pregunta.id, 'enunciado': pregunta.enunciado},
        'correcta': {'id': correcta.id, 'texto': correcta.texto} if correcta else None,
        'aciertos': respuestas.filter(correcta=True).count(),
        'respondidas': respuestas.count(),
        'jugadores': sala.participantes.count(),
        'top': _ranking(sala),
    }


def _podio(sala):
    return {'tipo': 'podio', 'top': _ranking(sala, limite=10), 'jugadores': sala.participantes.count()}


def mi_situacion(pin, usuario):
    """Datos privados de un estudiante: su puntaje, posición y cómo le fue en la última pregunta."""
    sala = Sala.objects.get(pin=pin)
    p = Participante.objects.filter(sala=sala, usuario=usuario).first()
    if p is None:
        return None
    posicion = sala.participantes.filter(puntaje__gt=p.puntaje).count() + 1
    datos = {'puntaje': p.puntaje, 'posicion': posicion, 'puntos_cuenta': p.puntos_cuenta}
    if sala.indice_actual >= 0:
        pregunta_id = SalaPregunta.objects.get(sala=sala, orden=sala.indice_actual).pregunta_id
        r = RespuestaReto.objects.filter(participante=p, pregunta_id=pregunta_id).first()
        datos['respondio'] = r is not None
        if sala.estado != Sala.PREGUNTA:   # el resultado solo se revela con la pregunta cerrada
            datos['ultima'] = {'correcta': r.correcta, 'puntos': r.puntos} if r else None
    if sala.estado == Sala.FINALIZADA:
        u = get_user_model().objects.get(pk=usuario.pk)   # en el WebSocket `usuario` es un objeto perezoso
        datos['cuenta'] = {'puntos': u.puntos, 'disponibles': u.puntos_disponibles, 'nivel': u.nivel}
    return datos


def estado_actual(pin, usuario):
    """
    Foto completa de la sala para quien se (re)conecta (RF-08): estado, pregunta abierta con
    el tiempo restante, último resultado o podio, y los datos propios del estudiante.
    """
    sala = Sala.objects.get(pin=pin)
    datos = {
        'tipo': 'estado',
        'estado': sala.estado,
        'pin': sala.pin,
        'total': sala.total_preguntas,
        'indice': sala.indice_actual,
        'segundos': sala.segundos,
        'jugadores': lista_jugadores(pin),
    }
    if sala.estado == Sala.PREGUNTA:
        pregunta = _pregunta_en(sala, sala.indice_actual)
        datos['actual'] = _datos_pregunta(sala, pregunta)
        datos['conteo'] = _conteo(sala, pregunta.id)
    elif sala.estado == Sala.RESULTADOS:
        datos['actual'] = _resultados(sala)
    elif sala.estado == Sala.FINALIZADA:
        datos['actual'] = _podio(sala)
    if sala.docente_id != usuario.pk:
        datos['yo'] = mi_situacion(pin, usuario)
    return datos


# ---------------------------------------------------------------------------
# Acciones del docente
# ---------------------------------------------------------------------------
def abrir_siguiente_pregunta(pin):
    """
    «Siguiente»: abre la próxima pregunta y guarda la hora de inicio. Si ya no quedan,
    finaliza la partida. Devuelve el evento a difundir, o None si no corresponde.
    """
    with transaction.atomic():
        sala = Sala.objects.select_for_update().get(pin=pin)
        if sala.estado not in (Sala.ESPERA, Sala.RESULTADOS):
            return None
        if sala.indice_actual + 1 >= sala.total_preguntas:
            return _finalizar(sala)
        sala.indice_actual += 1
        sala.estado = Sala.PREGUNTA
        sala.iniciada_en = timezone.now()
        sala.save(update_fields=['indice_actual', 'estado', 'iniciada_en'])
        return _datos_pregunta(sala, _pregunta_en(sala, sala.indice_actual))


def cerrar_y_rankear(pin, indice=None):
    """
    Cierra la pregunta abierta y devuelve los resultados. Es idempotente: si ya estaba
    cerrada (o `indice` no es la pregunta abierta, p. ej. un temporizador viejo) devuelve None.
    """
    with transaction.atomic():
        sala = Sala.objects.select_for_update().get(pin=pin)
        if sala.estado != Sala.PREGUNTA or (indice is not None and indice != sala.indice_actual):
            return None
        sala.estado = Sala.RESULTADOS
        sala.save(update_fields=['estado'])
        return _resultados(sala)


def cerrar_si_vencida(pin):
    """Si la pregunta abierta ya superó su tiempo (p. ej. el docente se desconectó), la cierra."""
    sala = Sala.objects.filter(pin=pin, estado=Sala.PREGUNTA).first()
    if sala and _ms_transcurridos(sala) > (sala.segundos + 1) * 1000:
        return cerrar_y_rankear(pin, sala.indice_actual)
    return None


def finalizar(pin):
    """El docente termina la partida antes de tiempo (no se puede con una pregunta abierta)."""
    with transaction.atomic():
        sala = Sala.objects.select_for_update().get(pin=pin)
        if sala.estado not in (Sala.ESPERA, Sala.RESULTADOS):
            return None
        return _finalizar(sala)


def _finalizar(sala):
    """
    RF-09: marca la sala como finalizada y suma a cada cuenta los puntos de la partida
    escalados a máximo 100. Corre dentro de la transacción que bloquea la sala, así que
    solo ocurre una vez.
    """
    sala.estado = Sala.FINALIZADA
    sala.save(update_fields=['estado'])
    maximo = PUNTOS_MAXIMOS * max(1, sala.indice_actual + 1)   # solo cuentan las preguntas jugadas
    for p in sala.participantes.select_related('usuario'):
        p.puntos_cuenta = min(PUNTOS_CUENTA_MAXIMOS, round(p.puntaje * PUNTOS_CUENTA_MAXIMOS / maximo))
        p.save(update_fields=['puntos_cuenta'])
        if p.puntos_cuenta > 0:
            p.usuario.sumar_puntos(p.puntos_cuenta)
    return _podio(sala)


# ---------------------------------------------------------------------------
# Respuestas de los estudiantes (RF-06)
# ---------------------------------------------------------------------------
def calcular_puntos(correcta, ms, segundos):
    """Puntos = 1000 × (1 − 0,5 × tiempo usado / tiempo límite) si acierta; 0 si falla."""
    if not correcta:
        return 0
    return round(PUNTOS_MAXIMOS * (1 - 0.5 * ms / (segundos * 1000)))


def registrar_respuesta(pin, usuario, pregunta_id, opcion_id):
    """Valida y puntúa una respuesta dentro de una transacción. Nunca revela si acertó."""
    try:
        pregunta_id, opcion_id = int(pregunta_id), int(opcion_id)
    except (TypeError, ValueError):
        return {'aceptada': False, 'motivo': 'respuesta inválida'}
    with transaction.atomic():
        sala = Sala.objects.select_for_update().get(pin=pin)
        if sala.estado != Sala.PREGUNTA:
            return {'aceptada': False, 'motivo': 'pregunta cerrada'}
        actual = SalaPregunta.objects.get(sala=sala, orden=sala.indice_actual).pregunta_id
        if actual != pregunta_id:
            return {'aceptada': False, 'motivo': 'pregunta cerrada'}
        ms = _ms_transcurridos(sala)
        if ms > sala.segundos * 1000:
            return {'aceptada': False, 'motivo': 'tiempo agotado'}
        opcion = Opcion.objects.filter(id=opcion_id, pregunta_id=pregunta_id).first()
        if opcion is None:
            return {'aceptada': False, 'motivo': 'opción inválida'}
        p = Participante.objects.filter(sala=sala, usuario=usuario).first()
        if p is None:
            return {'aceptada': False, 'motivo': 'no estás en esta sala'}
        puntos = calcular_puntos(opcion.correcta, ms, sala.segundos)
        try:
            with transaction.atomic():   # punto de guardado: el error no rompe la transacción externa
                RespuestaReto.objects.create(participante=p, pregunta_id=pregunta_id, opcion=opcion,
                                             correcta=opcion.correcta, tiempo_ms=ms, puntos=puntos)
        except IntegrityError:
            return {'aceptada': False, 'motivo': 'ya respondiste'}
        p.puntaje += puntos
        p.save(update_fields=['puntaje'])
        conteo = _conteo(sala, pregunta_id)
    return {'aceptada': True, 'conteo': conteo}
