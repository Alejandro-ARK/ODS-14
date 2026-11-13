"""
Pruebas del reto en vivo. Cubren los requerimientos RF-01 a RF-09 y las «pruebas mínimas»
de la sección 7 del documento técnico (QR vencido o alterado, doble respuesta, respuesta
tardía, que la respuesta correcta no viaje al cliente y la reconexión).
"""
import asyncio
import json
import time
from datetime import timedelta
from unittest import mock

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, Group
from django.core import signing
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from usuarios.models import Usuario

from . import servicios
from .models import GRUPO_DOCENTES, Opcion, Participante, Pregunta, RespuestaReto, Sala, es_docente
from .routing import websocket_urlpatterns
from .views import SAL_QR

CAPA_EN_MEMORIA = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


def crear_docente(correo='docente@test.co'):
    u = Usuario.objects.create_user(correo, 'clave-segura', nombre='Profe')
    u.groups.add(Group.objects.get(name=GRUPO_DOCENTES))
    return u


def crear_estudiante(correo='estu@test.co', nombre='Estu'):
    return Usuario.objects.create_user(correo, 'clave-segura', nombre=nombre)


def opcion(pregunta_id, correcta):
    return Opcion.objects.filter(pregunta_id=pregunta_id, correcta=correcta).first()


class BancoYRolTests(TestCase):
    def test_migracion_carga_banco_y_grupo(self):
        self.assertTrue(Group.objects.filter(name=GRUPO_DOCENTES).exists())
        self.assertGreaterEqual(Pregunta.objects.count(), 15)
        for p in Pregunta.objects.all():
            self.assertEqual(p.opciones.count(), 4)
            self.assertEqual(p.opciones.filter(correcta=True).count(), 1)

    def test_rol_docente(self):
        self.assertTrue(es_docente(crear_docente()))
        self.assertFalse(es_docente(crear_estudiante()))

    def test_solo_docentes_crean_salas(self):
        self.client.force_login(crear_estudiante())
        r = self.client.post(reverse('vivo:inicio'), {'cantidad': 5, 'segundos': 20})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Sala.objects.exists())

    def test_crear_sala(self):
        self.client.force_login(crear_docente())
        r = self.client.post(reverse('vivo:inicio'), {'cantidad': 7, 'segundos': 15})
        sala = Sala.objects.get()
        self.assertRedirects(r, reverse('vivo:sala', args=[sala.pin]))
        self.assertRegex(sala.pin, r'^\d{6}$')
        self.assertEqual(sala.total_preguntas, 7)
        self.assertEqual(sala.segundos, 15)

    def test_limites_de_la_sala(self):
        self.client.force_login(crear_docente())
        for datos in ({'cantidad': 4, 'segundos': 20}, {'cantidad': 16, 'segundos': 20},
                      {'cantidad': 5, 'segundos': 9}, {'cantidad': 5, 'segundos': 31}):
            r = self.client.post(reverse('vivo:inicio'), datos)
            self.assertEqual(r.status_code, 200, datos)
        self.assertFalse(Sala.objects.exists())

    def test_panel_hace_docente(self):
        admin = Usuario.objects.create_superuser('admin@test.co', 'clave-segura', nombre='Admin')
        estu = crear_estudiante()
        self.client.force_login(admin)
        self.client.post(reverse('panel:usuario_docente', args=[estu.pk]))
        self.assertTrue(es_docente(estu))
        self.client.post(reverse('panel:usuario_docente', args=[estu.pk]))
        self.assertFalse(es_docente(estu))


class QrTests(TestCase):
    def setUp(self):
        self.docente = crear_docente()
        self.sala = servicios.crear_sala(self.docente, 5, 20)
        self.estu = crear_estudiante()

    def token(self, hace_segundos=0):
        with mock.patch('django.core.signing.time.time', return_value=time.time() - hace_segundos):
            return signing.dumps({'s': self.sala.id}, salt=SAL_QR)

    def test_qr_es_svg_y_solo_para_el_docente(self):
        self.client.force_login(self.docente)
        r = self.client.get(reverse('vivo:qr', args=[self.sala.pin]))
        self.assertEqual(r['Content-Type'], 'image/svg+xml')
        self.assertIn(b'<svg', r.content)
        self.client.force_login(self.estu)
        self.assertEqual(self.client.get(reverse('vivo:qr', args=[self.sala.pin])).status_code, 404)

    def test_qr_valido_une_al_estudiante(self):
        self.client.force_login(self.estu)
        r = self.client.get(reverse('vivo:unirse') + '?t=' + self.token())
        self.assertRedirects(r, reverse('vivo:sala', args=[self.sala.pin]))
        self.assertTrue(Participante.objects.filter(sala=self.sala, usuario=self.estu).exists())

    def test_qr_de_hace_11_minutos_esta_vencido(self):
        self.client.force_login(self.estu)
        r = self.client.get(reverse('vivo:unirse') + '?t=' + self.token(hace_segundos=11 * 60))
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, 'QR vencido', status_code=400)
        self.assertFalse(Participante.objects.exists())

    def test_qr_de_hace_9_minutos_sigue_valido(self):
        self.client.force_login(self.estu)
        r = self.client.get(reverse('vivo:unirse') + '?t=' + self.token(hace_segundos=9 * 60))
        self.assertEqual(r.status_code, 302)

    def test_token_alterado_se_rechaza(self):
        t = self.token()
        alterado = t[:-1] + ('A' if t[-1] != 'A' else 'B')
        self.client.force_login(self.estu)
        r = self.client.get(reverse('vivo:unirse') + '?t=' + alterado)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Participante.objects.exists())

    def test_sin_sesion_pide_login_y_conserva_el_token(self):
        url = reverse('vivo:unirse') + '?t=' + self.token()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('usuarios:login'), r['Location'])
        self.assertIn('next=', r['Location'])

    def test_registro_vuelve_al_qr(self):
        url = reverse('vivo:unirse') + '?t=' + self.token()
        r = self.client.post(reverse('usuarios:registro') + '?next=' + url, {
            'nombre': 'Nueva', 'correo': 'nueva@test.co', 'contrasena': 'clave-segura', 'contrasena2': 'clave-segura'})
        self.assertEqual(r['Location'], url)

    def test_unirse_con_pin(self):
        self.client.force_login(self.estu)
        r = self.client.post(reverse('vivo:unirse_pin'), {'pin': self.sala.pin})
        self.assertRedirects(r, reverse('vivo:sala', args=[self.sala.pin]))
        r = self.client.post(reverse('vivo:unirse_pin'), {'pin': '999999' if self.sala.pin != '999999' else '000000'})
        self.assertRedirects(r, reverse('vivo:inicio'))

    def test_sala_finalizada_no_admite_nuevos(self):
        self.sala.estado = Sala.FINALIZADA
        self.sala.save()
        self.client.force_login(self.estu)
        self.assertEqual(self.client.get(reverse('vivo:unirse') + '?t=' + self.token()).status_code, 400)

    def test_pantallas(self):
        self.client.force_login(self.docente)
        self.assertTemplateUsed(self.client.get(reverse('vivo:sala', args=[self.sala.pin])), 'vivo/docente.html')
        self.client.force_login(self.estu)
        # Sin haberse unido no entra a la sala
        self.assertRedirects(self.client.get(reverse('vivo:sala', args=[self.sala.pin])), reverse('vivo:inicio'))
        Participante.objects.create(sala=self.sala, usuario=self.estu)
        self.assertTemplateUsed(self.client.get(reverse('vivo:sala', args=[self.sala.pin])), 'vivo/estudiante.html')


class PartidaTests(TestCase):
    """Lógica del servidor: RF-05 a RF-09."""

    def setUp(self):
        self.docente = crear_docente()
        self.sala = servicios.crear_sala(self.docente, 5, 20)
        self.pin = self.sala.pin
        self.a = crear_estudiante('a@test.co', 'Ana')
        self.b = crear_estudiante('b@test.co', 'Beto')
        for u in (self.a, self.b):
            Participante.objects.create(sala=self.sala, usuario=u)

    def abrir(self):
        return servicios.abrir_siguiente_pregunta(self.pin)

    def test_la_pregunta_no_lleva_la_respuesta(self):
        evento = self.abrir()
        self.assertEqual(evento['tipo'], 'pregunta')
        self.assertEqual(len(evento['pregunta']['opciones']), 4)
        self.assertNotIn('correcta', json.dumps(evento))
        estado = servicios.estado_actual(self.pin, self.a)
        self.assertNotIn('correcta', json.dumps(estado))

    def test_formula_de_puntaje(self):
        self.assertEqual(servicios.calcular_puntos(True, 0, 20), 1000)
        self.assertEqual(servicios.calcular_puntos(True, 10_000, 20), 750)
        self.assertEqual(servicios.calcular_puntos(True, 20_000, 20), 500)
        self.assertEqual(servicios.calcular_puntos(False, 1, 20), 0)

    def test_responder_dos_veces_se_rechaza(self):
        pid = self.abrir()['pregunta']['id']
        r1 = servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        r2 = servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, False).id)
        self.assertTrue(r1['aceptada'])
        self.assertEqual(r2, {'aceptada': False, 'motivo': 'ya respondiste'})
        self.assertEqual(RespuestaReto.objects.count(), 1)

    def test_respuesta_tardia_se_rechaza(self):
        pid = self.abrir()['pregunta']['id']
        Sala.objects.filter(pk=self.sala.pk).update(iniciada_en=timezone.now() - timedelta(seconds=21))
        r = servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        self.assertEqual(r, {'aceptada': False, 'motivo': 'tiempo agotado'})

    def test_respuesta_a_pregunta_cerrada_o_ajena(self):
        pid = self.abrir()['pregunta']['id']
        otra = Pregunta.objects.exclude(pk=pid).first()
        r = servicios.registrar_respuesta(self.pin, self.a, otra.id, opcion(otra.id, True).id)
        self.assertFalse(r['aceptada'])
        servicios.cerrar_y_rankear(self.pin)
        r = servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        self.assertEqual(r['motivo'], 'pregunta cerrada')

    def test_no_revela_si_acerto_antes_de_cerrar(self):
        pid = self.abrir()['pregunta']['id']
        r = servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        self.assertNotIn('correcta', json.dumps(r))
        self.assertNotIn('puntos', json.dumps(r))
        self.assertNotIn('ultima', servicios.mi_situacion(self.pin, self.a))

    def test_resultados_y_ranking(self):
        pid = self.abrir()['pregunta']['id']
        servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        servicios.registrar_respuesta(self.pin, self.b, pid, opcion(pid, False).id)
        r = servicios.cerrar_y_rankear(self.pin)
        self.assertEqual(r['tipo'], 'resultados')
        self.assertEqual(r['correcta']['id'], opcion(pid, True).id)
        self.assertEqual((r['aciertos'], r['respondidas'], r['jugadores']), (1, 2, 2))
        self.assertEqual(r['top'][0]['nombre'], 'Ana')
        self.assertIsNone(servicios.cerrar_y_rankear(self.pin))   # idempotente
        yo = servicios.mi_situacion(self.pin, self.b)
        self.assertEqual(yo['ultima'], {'correcta': False, 'puntos': 0})
        self.assertEqual(yo['posicion'], 2)

    def test_temporizador_viejo_no_cierra_otra_pregunta(self):
        self.abrir()
        servicios.cerrar_y_rankear(self.pin)
        self.abrir()   # pregunta 2
        self.assertIsNone(servicios.cerrar_y_rankear(self.pin, indice=0))
        self.assertEqual(Sala.objects.get(pk=self.sala.pk).estado, Sala.PREGUNTA)

    def test_reconexion_recupera_pregunta_tiempo_y_puntaje(self):
        pid = self.abrir()['pregunta']['id']
        servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        estado = servicios.estado_actual(self.pin, self.a)
        self.assertEqual(estado['estado'], 'pregunta')
        self.assertEqual(estado['actual']['pregunta']['id'], pid)
        self.assertGreater(estado['actual']['restante_ms'], 15_000)
        self.assertTrue(estado['yo']['respondio'])
        self.assertGreater(estado['yo']['puntaje'], 900)

    def test_cierre_perezoso_si_vencio(self):
        self.abrir()
        Sala.objects.filter(pk=self.sala.pk).update(iniciada_en=timezone.now() - timedelta(seconds=25))
        self.assertEqual(servicios.cerrar_si_vencida(self.pin)['tipo'], 'resultados')

    def test_partida_completa_suma_puntos_a_la_cuenta_una_vez(self):
        for _ in range(5):
            pid = self.abrir()['pregunta']['id']
            servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
            servicios.cerrar_y_rankear(self.pin)
        podio = self.abrir()   # «Siguiente» después de la última → podio
        self.assertEqual(podio['tipo'], 'podio')
        self.assertEqual(podio['top'][0]['nombre'], 'Ana')

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        pa = Participante.objects.get(usuario=self.a)
        self.assertTrue(90 <= pa.puntos_cuenta <= 100)   # ~5000 pts de partida → ~100 a la cuenta
        self.assertEqual(self.a.puntos, pa.puntos_cuenta)
        self.assertEqual(self.a.nivel, Usuario.calcular_nivel(self.a.puntos))
        self.assertEqual(self.b.puntos, 0)

        self.assertIsNone(self.abrir())                  # ya finalizada: no se suma dos veces
        self.assertIsNone(servicios.finalizar(self.pin))
        self.a.refresh_from_db()
        self.assertEqual(self.a.puntos, pa.puntos_cuenta)

    def test_terminar_antes_escala_por_preguntas_jugadas(self):
        pid = self.abrir()['pregunta']['id']
        servicios.registrar_respuesta(self.pin, self.a, pid, opcion(pid, True).id)
        servicios.cerrar_y_rankear(self.pin)
        servicios.finalizar(self.pin)
        self.assertGreaterEqual(Participante.objects.get(usuario=self.a).puntos_cuenta, 95)


@override_settings(CHANNEL_LAYERS=CAPA_EN_MEMORIA)
class WebSocketTests(TransactionTestCase):
    """El consumidor de extremo a extremo, con varios clientes conectados a la vez."""
    serialized_rollback = True   # conserva el banco de preguntas cargado por la migración

    def setUp(self):
        self.docente = crear_docente()
        self.sala = servicios.crear_sala(self.docente, 5, 10)
        self.estudiantes = [crear_estudiante(f'e{i}@test.co', f'Estu {i}') for i in range(3)]
        for u in self.estudiantes:
            Participante.objects.create(sala=self.sala, usuario=u)

    async def conectar(self, usuario):
        com = WebsocketCommunicator(URLRouter(websocket_urlpatterns), f'/ws/vivo/{self.sala.pin}/')
        # Igual que AuthMiddlewareStack: el usuario llega envuelto en un objeto perezoso.
        com.scope['user'] = SimpleLazyObject(lambda: usuario)
        conectado, _ = await com.connect()
        return com, conectado

    async def recibir_hasta(self, com, tipo):
        for _ in range(20):
            ev = await com.receive_json_from(timeout=3)
            if ev['tipo'] == tipo:
                return ev
        raise AssertionError(f'No llegó «{tipo}»')

    async def test_anonimo_o_ajeno_no_conecta(self):
        _, ok = await self.conectar(AnonymousUser())
        self.assertFalse(ok)
        intruso = await sync_to_async(crear_estudiante)('x@test.co', 'Intruso')
        _, ok = await self.conectar(intruso)
        self.assertFalse(ok)

    async def test_flujo_en_vivo(self):
        profe, ok = await self.conectar(self.docente)
        self.assertTrue(ok)
        self.assertEqual((await profe.receive_json_from())['tipo'], 'estado')

        clientes = []
        for u in self.estudiantes:
            com, ok = await self.conectar(u)
            self.assertTrue(ok)
            self.assertEqual((await com.receive_json_from())['tipo'], 'estado')
            clientes.append(com)
        lobby = await self.recibir_hasta(profe, 'lobby')
        self.assertEqual(len(lobby['jugadores']), 3)

        # «Siguiente»: todos reciben la misma pregunta, sin la respuesta correcta.
        await profe.send_json_to({'tipo': 'siguiente'})
        preguntas = [await self.recibir_hasta(c, 'pregunta') for c in clientes]
        self.assertEqual(len({p['pregunta']['id'] for p in preguntas}), 1)
        for p in preguntas:
            self.assertNotIn('correcta', json.dumps(p))

        pid = preguntas[0]['pregunta']['id']
        buena = await sync_to_async(opcion)(pid, True)
        mala = await sync_to_async(opcion)(pid, False)

        await clientes[0].send_json_to({'tipo': 'responder', 'pregunta': pid, 'opcion': buena.id})
        r = await self.recibir_hasta(clientes[0], 'respuesta_recibida')
        self.assertEqual(r, {'tipo': 'respuesta_recibida', 'aceptada': True})
        await clientes[0].send_json_to({'tipo': 'responder', 'pregunta': pid, 'opcion': mala.id})
        r = await self.recibir_hasta(clientes[0], 'respuesta_recibida')
        self.assertEqual(r['motivo'], 'ya respondiste')

        conteo = await self.recibir_hasta(profe, 'conteo')
        self.assertEqual(conteo['respondidas'], 1)

        # Un estudiante no puede manejar la partida.
        await clientes[1].send_json_to({'tipo': 'cerrar'})
        await asyncio.sleep(0.3)
        sala = await sync_to_async(Sala.objects.get)(pk=self.sala.pk)
        self.assertEqual(sala.estado, Sala.PREGUNTA)

        # Reconexión (modo avión): vuelve con la pregunta, el tiempo y su puntaje.
        await clientes[0].disconnect()
        clientes[0], ok = await self.conectar(self.estudiantes[0])
        estado = await clientes[0].receive_json_from()
        self.assertEqual(estado['estado'], 'pregunta')
        self.assertEqual(estado['actual']['pregunta']['id'], pid)
        self.assertTrue(estado['yo']['respondio'])
        self.assertGreater(estado['yo']['puntaje'], 0)

        # El docente cierra: llega la respuesta correcta, el top 5 y el resultado propio.
        await profe.send_json_to({'tipo': 'cerrar'})
        res = await self.recibir_hasta(clientes[0], 'resultados')
        self.assertEqual(res['correcta']['id'], buena.id)
        self.assertTrue(res['yo']['ultima']['correcta'])
        self.assertEqual(res['top'][0]['nombre'], 'Estu 0')
        res_otro = await self.recibir_hasta(clientes[1], 'resultados')
        self.assertIsNone(res_otro['yo']['ultima'])

        await profe.send_json_to({'tipo': 'finalizar'})
        podio = await self.recibir_hasta(clientes[0], 'podio')
        self.assertGreater(podio['yo']['puntos_cuenta'], 0)
        self.assertEqual(podio['yo']['cuenta']['puntos'], podio['yo']['puntos_cuenta'])

        for c in [profe, *clientes]:
            await c.disconnect()

    async def test_el_tiempo_cierra_la_pregunta_solo(self):
        await sync_to_async(Sala.objects.filter(pk=self.sala.pk).update)(segundos=1)
        profe, _ = await self.conectar(self.docente)
        await profe.receive_json_from()
        await profe.send_json_to({'tipo': 'siguiente'})
        await self.recibir_hasta(profe, 'pregunta')
        res = await self.recibir_hasta(profe, 'resultados')   # tras 1 s + 1 s de gracia
        self.assertEqual(res['respondidas'], 0)
        await profe.disconnect()
