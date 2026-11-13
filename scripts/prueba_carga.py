"""
Prueba de carga del reto en vivo (documento técnico, sección 7).

Crea (o reutiliza) N cuentas de prueba, las une a una sala con el PIN, abre N WebSockets a la
vez y responde cada pregunta con una opción al azar tras una espera aleatoria. Al final
muestra cuántos se conectaron, cuántas respuestas se aceptaron y el puesto de cada uno.

Uso (con la sala ya creada por un docente y su pantalla abierta):

    pip install websockets
    python scripts/prueba_carga.py --url https://ods-14.onrender.com --pin 123456 --jugadores 30

Después, en la pantalla del docente, pulsa «Comenzar» y avanza las preguntas.
Las cuentas se llaman carga1@prueba.test, carga2@prueba.test… (contraseña: Carga-Oceano-2026).
"""
import argparse
import asyncio
import http.cookiejar
import json
import random
import re
import time
import urllib.parse
import urllib.request

import websockets

CLAVE = 'Carga-Oceano-2026'


class Cliente:
    """Navegador mínimo: guarda cookies y envía formularios con CSRF."""

    def __init__(self, base):
        self.base = base.rstrip('/')
        self.cookies = http.cookiejar.CookieJar()
        self.http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def cookie(self, nombre):
        return next((c.value for c in self.cookies if c.name == nombre), None)

    def get(self, ruta):
        with self.http.open(self.base + ruta) as r:
            return r.geturl(), r.read().decode()

    def post(self, ruta, datos):
        _, html = self.get(ruta)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        datos = dict(datos, csrfmiddlewaretoken=token.group(1) if token else self.cookie('csrftoken'))
        req = urllib.request.Request(self.base + ruta, data=urllib.parse.urlencode(datos).encode(),
                                     headers={'Referer': self.base + ruta})
        with self.http.open(req) as r:
            return r.geturl(), r.read().decode()

    def entrar(self, correo, nombre, pin):
        self.post('/registro/', {'nombre': nombre, 'correo': correo, 'contrasena': CLAVE, 'contrasena2': CLAVE})
        if not self.cookie('sessionid'):   # la cuenta ya existía: iniciar sesión
            self.post('/login/', {'correo': correo, 'contrasena': CLAVE})
        if not self.cookie('sessionid'):
            raise RuntimeError(f'No se pudo iniciar sesión con {correo}')
        destino, _ = self._unirse(pin)
        if f'/vivo/sala/{pin}/' not in destino:
            raise RuntimeError(f'{correo} no pudo unirse a la sala {pin}')

    def _unirse(self, pin):
        _, html = self.get('/vivo/')
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
        req = urllib.request.Request(self.base + '/vivo/unirse/pin/',
                                     data=urllib.parse.urlencode({'pin': pin, 'csrfmiddlewaretoken': token}).encode(),
                                     headers={'Referer': self.base + '/vivo/'})
        with self.http.open(req) as r:
            return r.geturl(), r.read().decode()


async def jugador(i, args, stats):
    cliente = Cliente(args.url)
    await asyncio.to_thread(cliente.entrar, f'carga{i}@prueba.test', f'Bot {i}', args.pin)
    ws_url = re.sub(r'^http', 'ws', args.url.rstrip('/')) + f'/ws/vivo/{args.pin}/'
    cabeceras = {'Cookie': f'sessionid={cliente.cookie("sessionid")}'}
    async with websockets.connect(ws_url, additional_headers=cabeceras, origin=args.url.rstrip('/')) as ws:
        stats['conectados'] += 1
        async for crudo in ws:
            ev = json.loads(crudo)
            if ev['tipo'] == 'pregunta' or (ev['tipo'] == 'estado' and ev['estado'] == 'pregunta'
                                            and not ev['yo']['respondio']):
                p = ev if ev['tipo'] == 'pregunta' else ev['actual']
                stats['preguntas'] += 1
                await asyncio.sleep(random.uniform(0.3, min(5, p['restante_ms'] / 1000)))
                op = random.choice(p['pregunta']['opciones'])
                await ws.send(json.dumps({'tipo': 'responder', 'pregunta': p['pregunta']['id'], 'opcion': op['id']}))
            elif ev['tipo'] == 'respuesta_recibida':
                stats['aceptadas' if ev['aceptada'] else 'rechazadas'] += 1
            elif ev['tipo'] == 'podio':
                stats['final'][f'Bot {i}'] = (ev['yo']['posicion'], ev['yo']['puntaje'], ev['yo']['puntos_cuenta'])
                return


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', required=True, help='p. ej. https://ods-14.onrender.com')
    ap.add_argument('--pin', required=True)
    ap.add_argument('--jugadores', type=int, default=30)
    args = ap.parse_args()

    stats = {'conectados': 0, 'preguntas': 0, 'aceptadas': 0, 'rechazadas': 0, 'final': {}}
    inicio = time.monotonic()
    tareas = [asyncio.create_task(jugador(i, args, stats)) for i in range(1, args.jugadores + 1)]

    async def informe():
        while True:
            await asyncio.sleep(5)
            print(f"[{time.monotonic() - inicio:5.0f}s] conectados={stats['conectados']} "
                  f"respuestas aceptadas={stats['aceptadas']} rechazadas={stats['rechazadas']}")
    reporte = asyncio.create_task(informe())
    resultados = await asyncio.gather(*tareas, return_exceptions=True)
    reporte.cancel()

    errores = [r for r in resultados if isinstance(r, Exception)]
    print(f"\nJugadores conectados: {stats['conectados']}/{args.jugadores}")
    print(f"Respuestas aceptadas: {stats['aceptadas']} · rechazadas: {stats['rechazadas']}")
    for nombre, (pos, pts, cuenta) in sorted(stats['final'].items(), key=lambda x: x[1][0]):
        print(f'  {pos:>2}. {nombre:<8} {pts:>6} pts  (+{cuenta} a la cuenta)')
    for e in errores[:5]:
        print('Error:', repr(e))


if __name__ == '__main__':
    asyncio.run(main())
