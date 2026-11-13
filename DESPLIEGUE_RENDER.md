# Desplegar Misión Océano en Render

Desde que existe el **Reto en vivo**, la aplicación necesita tres piezas en Render:

| Pieza | Para qué | Plan |
|---|---|---|
| **Web Service** (Python) | Ejecuta Django con **Daphne** (HTTP + WebSockets) | Free |
| **PostgreSQL** | Cuentas, puntos, tienda, salas, respuestas | Free (vence a los 30 días) |
| **Key Value** (Redis) | Capa de canales: envía cada pregunta a todos los celulares a la vez | Free (25 MB, solo memoria) |

> En Render el disco es efímero: **SQLite no sirve** (se borraría en cada despliegue). Las tablas
> se crean solas con `migrate` en cada despliegue (lo hace `build.sh`).

Archivos que ya están listos en el repositorio: `build.sh`, `render.yaml`, `requirements.txt`
(channels, channels-redis, daphne, qrcode, WhiteNoise, dj-database-url, psycopg) y
`config/settings.py` (lee `DATABASE_URL`, `REDIS_URL` y `RENDER_EXTERNAL_HOSTNAME`).

---

## 0. Antes de subir: probar en tu computador

```bash
python -m venv venv
venv\Scripts\activate                 # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate               # crea las tablas vivo_* y carga 23 preguntas + grupo «Docentes»
python manage.py test                  # deben pasar todas (141)
python manage.py runserver             # con daphne instalado, runserver ya sirve WebSockets
```

En local no necesitas Redis: sin `REDIS_URL` se usa una capa en memoria (solo vale para un
proceso). Para probar con celulares en la misma red Wi-Fi: `python manage.py runserver 0.0.0.0:8000`,
agrega la IP de tu PC a `DJANGO_ALLOWED_HOSTS` en `.env` y entra desde el celular a `http://IP:8000`.

## 1. Subir los cambios a GitHub

El repositorio debe tener `manage.py`, `build.sh` y `render.yaml` **en la raíz** (no dentro de
una carpeta `ODS-14-main/`). Desde la carpeta del proyecto:

```bash
git checkout -b reto-en-vivo           # rama nueva para revisar el cambio entre los dos
git add .
git commit -m "Reto en vivo: Channels, QR dinámico, ranking en tiempo real"
git push -u origin reto-en-vivo
```

En GitHub abre un **Pull Request** hacia `main`, que tu compañero lo revise y haz **Merge**.
Render despliega cuando el cambio llega a `main`. Verifica antes de hacer merge que **no** subas
`.env`, `db.sqlite3`, `venv/` ni `staticfiles/` (`.gitignore` ya los excluye).

---

## 2A. Si YA tienen el servicio en Render (ods-14.onrender.com) — lo más probable

Hay que hacer **tres cosas** en el panel de Render **antes** de hacer merge a `main`
(si haces merge primero, el despliegue arranca con gunicorn y el reto en vivo no funciona).

### Paso 1 · Crear el Redis (Key Value)
1. <https://dashboard.render.com> → **New → Key Value**.
2. Nombre: `mision-oceano-redis` · **Región: la MISMA del Web Service** (p. ej. Oregon) ·
   Plan **Free** · *Maxmemory policy*: `noeviction`.
3. **Create Key Value**. Cuando quede *Available*, copia la **Internal Key Value URL**
   (empieza por `redis://red-…:6379`).

   ⚠️ Usa la **Internal**, no la External. La interna solo funciona desde servicios de
   Render en la misma región, que es justo lo que queremos.

### Paso 2 · Agregar la variable al Web Service
Web Service → **Environment** → **Add Environment Variable**:

| Variable | Valor |
|---|---|
| `REDIS_URL` | la Internal Key Value URL del paso 1 |

Revisa que sigan estas (ya deberían existir): `PYTHON_VERSION=3.12.3`, `DJANGO_DEBUG=0`,
`DJANGO_SECRET_KEY`, `DATABASE_URL`. Guarda con **Save, rebuild, and deploy** o
**Save only** (si aún no hiciste merge).

### Paso 3 · Cambiar el comando de inicio
Web Service → **Settings** → **Build & Deploy** → **Start Command** → **Edit**:

```
daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

(antes era `gunicorn config.wsgi:application`; gunicorn no entiende WebSockets).
El **Build Command** sigue igual: `bash build.sh`.

### Paso 4 · Desplegar
Haz **Merge** del Pull Request a `main`. Render detecta el push y despliega solo. En **Logs**
deberías ver algo como:

```
Applying vivo.0001_inicial... OK
Applying vivo.0002_banco_y_docentes... OK
...
Starting server at tcp:port=10000:interface=0.0.0.0
Listening on TCP address 0.0.0.0:10000
==> Your service is live 🎉
```

Si no se despliega solo: **Manual Deploy → Deploy latest commit**.

---

## 2B. Si van a crear todo de cero: Blueprint (un solo clic)

1. <https://dashboard.render.com> → **New → Blueprint** → elige el repositorio.
2. Render lee `render.yaml` y propone crear **3 recursos**: la base `mision-oceano-db`,
   el Key Value `mision-oceano-redis` y el servicio web `mision-oceano` (ya con
   `REDIS_URL`, `DATABASE_URL` y el comando de Daphne conectados).
3. Te pedirá `DJANGO_SUPERUSER_CORREO`, `DJANGO_SUPERUSER_NOMBRE` y
   `DJANGO_SUPERUSER_PASSWORD`: escribe los del administrador.
4. **Apply** y espera *Your service is live*.

> La cuenta Free solo permite **una** instancia Key Value activa por workspace. Si ya creaste
> una a mano, borra una de las dos o usa la opción 2A.

## 2C. Opción manual completa (sin Blueprint)

1. **New → PostgreSQL** (Free) → copia la **Internal Database URL**.
2. **New → Key Value** (Free, misma región) → copia la **Internal Key Value URL**.
3. **New → Web Service** → el repositorio:

| Campo | Valor |
|---|---|
| Runtime | Python 3 |
| Build Command | `bash build.sh` |
| Start Command | `daphne -b 0.0.0.0 -p $PORT config.asgi:application` |
| Root Directory | *(vacío)* |

4. **Environment**:

| Variable | Valor |
|---|---|
| `PYTHON_VERSION` | `3.12.3` |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | clave larga y aleatoria (botón *Generate*) |
| `DATABASE_URL` | Internal Database URL |
| `REDIS_URL` | Internal Key Value URL |
| `DJANGO_SUPERUSER_CORREO` / `_NOMBRE` / `_PASSWORD` | datos del administrador (opcional) |

**Alternativa a Render Key Value: Upstash.** Crea una base Redis gratis en <https://upstash.com>,
copia su URL `rediss://default:CLAVE@xxxx.upstash.io:6379` y ponla en `REDIS_URL`. No hay que
cambiar código (la doble *s* de `rediss://` activa TLS).

---

## 3. Después del despliegue: comprobar que todo funciona

1. Abre `https://ods-14.onrender.com/` (la primera carga puede tardar ~1 min si estaba dormido).
2. **Da el rol docente**: entra con el superusuario → **Panel** (`/panel/`) → **Usuarios** →
   botón **Docente** en la cuenta del profesor. (También en `/admin/` → Usuarios → *Grupos* →
   «Docentes»). Los superusuarios ya pueden crear salas.
3. Con la cuenta docente: **Reto en vivo** → *Crear una sala* (5–15 preguntas, 10–30 s).
4. Desde un celular con **datos móviles** (no la misma red) escanea el QR → inicia sesión o
   regístrate → deberías quedar en «¡Ya estás dentro!» y aparecer en la lista del docente.
5. Pulsa **Comenzar**. En la pantalla del docente, la etiqueta verde **«● En vivo»** indica que
   el WebSocket está conectado.

**Prueba de carga** (sección 7 del documento): con una sala creada y abierta en la pantalla
del docente, desde tu computador:

```bash
pip install websockets
python scripts/prueba_carga.py --url https://ods-14.onrender.com --pin 123456 --jugadores 30
```

Crea 30 cuentas `cargaN@prueba.test`, las une a la sala y responde al azar. Luego avanza las
preguntas desde la pantalla del docente. En nuestras pruebas locales (Daphne + Redis + PostgreSQL)
se conectaron 30/30 y se aceptaron 150/150 respuestas sin errores.

---

## 4. Problemas frecuentes del reto en vivo

| Síntoma | Causa probable | Solución |
|---|---|---|
| La etiqueta dice «Sin conexión · reconectando…» todo el tiempo | El Start Command sigue siendo `gunicorn` | Cámbialo a `daphne -b 0.0.0.0 -p $PORT config.asgi:application` y redepliega. |
| En Logs: `Error 111 connecting` / `Name or service not known` (Redis) | `REDIS_URL` vacía, mal copiada o Key Value en otra región | Usa la **Internal** URL y la misma región del Web Service. |
| En Logs: `Timeout reading from …:6379` | Versión de redis-py ≥ 8 con el tiempo de espera por defecto | Ya está resuelto en `settings.py` (`socket_timeout: 30`). Si lo ves, confirma que desplegaste la última versión. |
| El estudiante ve «QR vencido» | El QR tiene más de 10 min (o se escaneó una foto vieja) | Escanear el QR que se ve ahora en el tablero, o usar el PIN. |
| Al escanear pide iniciar sesión y luego no entra a la sala | Tardó más de 10 min en registrarse | Volver a escanear el QR o escribir el PIN en «Reto en vivo». |
| Un estudiante no ve «Crear sala» | No está en el grupo «Docentes» | Panel → Usuarios → **Docente**. |
| `403` al abrir el WebSocket | Origen no permitido o sin sesión | Con dominio propio, agrega el dominio a `DJANGO_ALLOWED_HOSTS`. |
| Tras un rato sin uso, la sala «se cae» | El servicio Free se durmió (15 min sin tráfico) o Redis Free se reinició | Al volver, los celulares se reconectan solos y recuperan la pregunta y su puntaje (todo vive en PostgreSQL). |
| `too many connections` en PostgreSQL | Conexiones persistentes con ASGI | Por defecto ya se usa `DB_CONN_MAX_AGE=0`; no lo subas en el plan Free. |

## Cosas a saber
- El plan gratuito del servicio web se **duerme tras 15 min sin tráfico** (peticiones HTTP o
  mensajes WebSocket) y tarda ~1 minuto en despertar. **Abre el sitio unos minutos antes de la
  clase** o de grabar el video.
- La base **PostgreSQL gratuita vence a los 30 días** de creada. Si la suya ya venció, crea
  otra y actualiza `DATABASE_URL`. Haz copias si guardas datos importantes.
- El **Key Value gratuito** guarda todo en memoria y Render puede reiniciarlo: no pasa nada,
  Channels solo lo usa para repartir mensajes; las salas y puntajes están en PostgreSQL.
- Cada `git push` a `main` vuelve a desplegar automáticamente.
- Si el sitio responde "Bad Request (400)", falta el dominio en `ALLOWED_HOSTS`
  (en Render se añade solo con `RENDER_EXTERNAL_HOSTNAME`; para un dominio propio usa
  `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`).

## Importar usuarios del sitio PHP (opcional)
El plan gratuito no incluye terminal (Shell). Ejecuta el comando desde tu computador apuntando a la
base de Render con su **External Database URL**:
```bash
set DATABASE_URL=postgres://...External...      # Windows  (Linux/Mac: export DATABASE_URL=...)
python manage.py importar_usuarios usuarios.csv
```
