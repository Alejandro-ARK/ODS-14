"""
Consumidor de WebSocket del reto en vivo (documento técnico, fase 3).

Cada celular (y la pantalla del docente) abre ws/vivo/<pin>/. Todas las conexiones de una
sala se unen al grupo «reto_<pin>» de la capa de canales (Redis en producción), así el
servidor puede enviar la misma pregunta a todos a la vez.
"""
import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import servicios

rol_en_sala = database_sync_to_async(servicios.rol_en_sala)
estado_actual = database_sync_to_async(servicios.estado_actual)
lista_jugadores = database_sync_to_async(servicios.lista_jugadores)
abrir_siguiente_pregunta = database_sync_to_async(servicios.abrir_siguiente_pregunta)
cerrar_y_rankear = database_sync_to_async(servicios.cerrar_y_rankear)
cerrar_si_vencida = database_sync_to_async(servicios.cerrar_si_vencida)
finalizar = database_sync_to_async(servicios.finalizar)
registrar_respuesta = database_sync_to_async(servicios.registrar_respuesta)
mi_situacion = database_sync_to_async(servicios.mi_situacion)


class RetoConsumer(AsyncJsonWebsocketConsumer):
    temporizador = None

    async def connect(self):
        self.pin = self.scope['url_route']['kwargs']['pin']
        self.usuario = self.scope['user']
        rol = await rol_en_sala(self.pin, self.usuario)   # 'docente', 'estudiante' o None
        if rol is None:
            await self.close()
            return
        self.es_docente = rol == 'docente'
        self.grupo = f'reto_{self.pin}'
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()

        # Si la pregunta abierta ya venció (p. ej. el docente perdió la conexión), se cierra ahora.
        resultado = await cerrar_si_vencida(self.pin)
        if resultado:
            await self.difundir(resultado)

        estado = await estado_actual(self.pin, self.usuario)
        await self.send_json(estado)   # sirve para reconectar (RF-08)
        if self.es_docente and estado['estado'] == 'pregunta':
            # El docente volvió con una pregunta abierta: se reprograma el cierre automático.
            self.temporizador = asyncio.create_task(self.cerrar_al_vencer(estado['actual']))
        if not self.es_docente:
            await self.difundir({'tipo': 'lobby', 'jugadores': await lista_jugadores(self.pin)})

    async def disconnect(self, codigo):
        if hasattr(self, 'grupo'):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive_json(self, contenido, **kwargs):
        tipo = contenido.get('tipo')
        if tipo == 'responder' and not self.es_docente:
            r = await registrar_respuesta(self.pin, self.usuario,
                                          contenido.get('pregunta'), contenido.get('opcion'))
            conteo = r.pop('conteo', None)
            await self.send_json({'tipo': 'respuesta_recibida', **r})   # solo a quien respondió
            if conteo:
                await self.difundir(conteo)   # el docente ve cuántos han respondido
        elif tipo == 'siguiente' and self.es_docente:
            evento = await abrir_siguiente_pregunta(self.pin)           # sin la respuesta correcta
            if evento:
                await self.difundir(evento)
                if evento['tipo'] == 'pregunta':
                    # En segundo plano, para que el docente pueda seguir enviando eventos.
                    self.temporizador = asyncio.create_task(self.cerrar_al_vencer(evento))
        elif tipo == 'cerrar' and self.es_docente:
            await self.cerrar_pregunta()
        elif tipo == 'finalizar' and self.es_docente:
            evento = await finalizar(self.pin)
            if evento:
                await self.difundir(evento)

    async def cerrar_al_vencer(self, evento):
        await asyncio.sleep(evento['restante_ms'] / 1000 + 1)
        await self.cerrar_pregunta(evento['indice'])

    async def cerrar_pregunta(self, indice=None):
        resultado = await cerrar_y_rankear(self.pin, indice)   # idempotente: si ya cerró, devuelve None
        if resultado:
            await self.difundir(resultado)

    async def difundir(self, evento):
        await self.channel_layer.group_send(self.grupo, {'type': 'reto.evento', 'evento': evento})

    async def reto_evento(self, mensaje):
        """Recibe los group_send con type 'reto.evento' y los reenvía a este navegador."""
        evento = dict(mensaje['evento'])
        if not self.es_docente and evento['tipo'] in ('resultados', 'podio'):
            # A cada estudiante se le agrega su propio resultado (solo lo ve él).
            evento['yo'] = await mi_situacion(self.pin, self.usuario)
        await self.send_json(evento)
