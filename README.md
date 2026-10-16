# 🌊 Misión Océano

Plataforma web educativa sobre el **ODS 14 – Vida submarina** de las Naciones Unidas
(*conservar y utilizar de forma sostenible los océanos, los mares y los recursos marinos*).

Quien la usa **aprende** sobre el océano, **juega**, responde un **quiz**, gana **puntos**, sube de **nivel** y
gasta esos puntos en una **tienda** para personalizar su **avatar**. Los administradores gestionan las
cuentas desde un **panel** propio. Está hecha con **Django** (Python).

| | |
|---|---|
| **Repositorio** | <https://github.com/Alejandro-ARK/ODS-14> |
| **Aplicación desplegada** | <https://ods-14.onrender.com> |
| **Base de datos** | PostgreSQL en producción · SQLite en desarrollo local |

### Integrantes

| Nombre completo | GitHub |
|---|---|
| *Luis Alejandro Hernandez Ozuna* | [@Alejandro-ARK](https://github.com/Alejandro-ARK) |
| *Eduardo Andres Espitia Rada* | [@Squarterder](https://github.com/Squarterder) |

---

## Contenido

1. [¿Qué hace la aplicación?](#1-qué-hace-la-aplicación)
2. [Tecnologías](#2-tecnologías)
3. [Cómo hacerlo funcionar](#3-cómo-hacerlo-funcionar)
4. [Cómo funciona el código](#4-cómo-funciona-el-código)
5. [Base de datos y diagramas](#5-base-de-datos-y-diagramas)
6. [Cómo colaborar](#6-cómo-colaborar)

---

## 1. ¿Qué hace la aplicación?

| Sección | Ruta | Qué ofrece |
|---|---|---|
| Inicio | `/` | Presentación del proyecto y accesos a todas las secciones. |
| Aprende | `/aprende/` | Contenido sobre el ODS 14: metas, ecosistemas marinos y amenazas. |
| Juega | `/juega/` | Dos minijuegos: **Recolecta la basura** y **Memoria marina**. |
| Quiz | `/quiz/` | 5 preguntas sobre el ODS 14. Cada acierto vale 10 puntos. |
| Nuestros mares | `/mares/` | El Caribe y el Pacífico colombianos y sus áreas marinas protegidas. |
| Actúa | `/actua/` | Lista de compromisos para cuidar el océano (se guarda en el navegador). |
| Registro / Inicio de sesión | `/registro/`, `/login/` | Creación de cuenta e ingreso con correo y contraseña. |
| Mi perfil | `/perfil/` | Avatar, nivel, puntos, insignias y cambio del nombre de perfil. |
| Tienda | `/tienda/` | Compra y cambio de partes del avatar usando los puntos ganados. |
| Panel de administración | `/panel/` | **Solo superusuarios**: resumen, gestión de cuentas y consulta de la base de datos. |
| Admin de Django | `/admin/` | Edición avanzada: cuentas, catálogo de partes del avatar y sus precios. |

---

## 2. Tecnologías

| Capa | Tecnología | Para qué se usa |
|---|---|---|
| Lenguaje | Python 3.10 o superior (recomendado 3.12) | Todo el backend. |
| Framework | **Django** 5.2 – 6.1 | Rutas, vistas, formularios, ORM, autenticación, administración, pruebas. |
| Base de datos | **PostgreSQL** (producción), **SQLite** (local), MySQL (opcional) | Almacenamiento de cuentas, catálogo y compras. |
| Interfaz | HTML5 + plantillas de Django, CSS propio, **Bootstrap 4.6**, Font Awesome 5 | Páginas y estilos. |
| Interactividad | JavaScript (sin framework) + jQuery/Bootstrap JS | Quiz, minijuegos, contador de puntos, menús. |
| Servidor de producción | **Gunicorn** + **WhiteNoise** | Ejecuta la app y sirve los archivos estáticos. |
| Hosting | **Render** (servicio web + PostgreSQL) enlazado a GitHub | Despliegue automático en cada `git push`. |
| Librerías | `psycopg` (PostgreSQL), `dj-database-url`, `bcrypt` | Conexión a la base y lectura de contraseñas con hash bcrypt. |

Todas las dependencias de Python están en `requirements.txt`.

---

## 3. Cómo hacerlo funcionar

### 3.1 Requisitos

- **Python 3.10 o superior** (`python --version`; en Windows también puede ser `py --version`).
- **Git** (o descargar el proyecto como ZIP desde GitHub).
- **Conexión a Internet** al abrir el sitio: Bootstrap y las tipografías se cargan desde un CDN.

### 3.2 Paso a paso (ejecución local con SQLite)

No necesitas instalar ninguna base de datos: por defecto se crea un archivo `db.sqlite3`.

```bash
# 1) Descargar el proyecto
git clone https://github.com/Alejandro-ARK/ODS-14.git
cd ODS-14

# 2) Crear y activar un entorno virtual
python -m venv venv
venv\Scripts\activate            # Windows (CMD)
# source venv/bin/activate       # Linux / macOS

# 3) Instalar las dependencias
pip install -r requirements.txt

# 4) Crear las tablas (y cargar el catálogo de partes del avatar)
python manage.py migrate

# 5) Crear tu cuenta de administrador (pide correo, nombre y contraseña)
python manage.py createsuperuser

# 6) Arrancar el servidor
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>. Para detener el servidor: `Ctrl + C`.

**Primeros pasos sugeridos**

1. Entra a <http://127.0.0.1:8000/registro/> y crea una cuenta de usuario.
2. Responde el **Quiz** (`/quiz/`) y pulsa *Guardar mis puntos*; mira cómo sube el contador de la barra.
3. Ve a la **Tienda** (`/tienda/`) y compra una parte del avatar con tus puntos.
4. Inicia sesión con la cuenta de administrador y abre <http://127.0.0.1:8000/panel/>.

### 3.3 Variables de entorno

La configuración se lee de variables de entorno o de un archivo **`.env`** en la raíz del proyecto
(copia `.env.example` como `.env` y edítalo). **El `.env` real nunca se sube a GitHub** (está en `.gitignore`).
En el archivo `.env` no pongas comentarios al final de la línea de un valor.

| Variable | Para qué sirve | Valor por defecto | ¿Obligatoria? |
|---|---|---|---|
| `DJANGO_DEBUG` | `1` = desarrollo (muestra errores detallados). `0` = producción. | `1` | No |
| `DJANGO_SECRET_KEY` | Clave secreta de Django (larga y aleatoria). | clave de desarrollo | **Sí**, si `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | Dominios permitidos, separados por comas. | `localhost,127.0.0.1` | No |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes `https://…` de confianza (solo con dominio propio). | vacío | Solo con dominio propio |
| `RENDER_EXTERNAL_HOSTNAME` | La define Render sola; se añade a los hosts permitidos y a los orígenes CSRF. | — | No |
| `DATABASE_URL` | URL de PostgreSQL. **Tiene prioridad** sobre las demás opciones de base de datos. | — | En producción |
| `DB_ENGINE` | `sqlite` o `mysql`. | `sqlite` | No |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Datos de conexión de MySQL (solo con `DB_ENGINE=mysql`). | `mision_oceano_django`, `root`, vacío, `localhost`, `3306` | No |
| `DJANGO_SECRET_KEY` aparte, `DJANGO_SUPERUSER_CORREO`, `DJANGO_SUPERUSER_NOMBRE`, `DJANGO_SUPERUSER_PASSWORD` | Las usa `build.sh` para crear un administrador durante el despliegue. | — | No |

### 3.4 Elegir la base de datos

El proyecto decide la base en este orden: **`DATABASE_URL`** → **MySQL** (si `DB_ENGINE=mysql`) → **SQLite**.

**PostgreSQL** (el motor del despliegue):

```bash
# 1) Crear una base vacía
createdb mision_oceano
# 2) Indicar la URL (en .env o como variable de entorno)
DATABASE_URL=postgresql://USUARIO:CLAVE@localhost:5432/mision_oceano
# 3) Crear las tablas
python manage.py migrate
```

**MySQL** (opcional): `pip install mysqlclient`, y en `.env` pon `DB_ENGINE=mysql` más los `DB_*`; luego `python manage.py migrate`.

### 3.5 Cargar la base de datos de ejemplo (dump)

La carpeta `database/` incluye `mision_oceano_dump.sql`, una copia de respaldo en PostgreSQL con **datos de ejemplo**:
el catálogo de 16 partes de avatar, 10 usuarios y 25 compras.

```bash
createdb mision_oceano
psql -d mision_oceano -f database/mision_oceano_dump.sql
# y apuntar la aplicación a esa base:
DATABASE_URL=postgresql://USUARIO:CLAVE@localhost:5432/mision_oceano
python manage.py runserver
```

Cuentas incluidas **en el dump** (existen solo si lo restauras):

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador (superusuario) | `admin@mision-oceano.test` | `Admin-Oceano-2026` |
| Usuario regular | `estudiante@mision-oceano.test` | `Usuario-Oceano-2026` |

Los otros 8 usuarios de ejemplo usan la contraseña del usuario regular; uno de ellos
(`andres.herrera@…`) está suspendido a propósito para ver cómo se muestra en el panel.

**Cargar el dump en la base de Render** (sirve para tener cuentas de prueba en el sitio desplegado).
⚠️ Esto **borra todo lo que haya** en esa base:

```bash
# Usa la "External Database URL" de tu PostgreSQL en Render
psql "EXTERNAL_DATABASE_URL" -c "DROP SCHEMA public CASCADE" -c "CREATE SCHEMA public"
psql "EXTERNAL_DATABASE_URL" -f database/mision_oceano_dump.sql
```

Hace falta vaciar el esquema porque `migrate` ya creó las tablas y el dump vuelve a crearlas.
Después, cada despliegue ejecuta `migrate` y responde *No migrations to apply*: no rompe nada.

### 3.6 Pruebas automáticas

```bash
python manage.py test                 # todas las pruebas
python manage.py test tienda          # solo la tienda
python manage.py test usuarios panel  # varias apps
```

Por defecto corren sobre SQLite. Si defines `DATABASE_URL` con PostgreSQL, Django crea y borra una base
temporal llamada `test_<nombre>` (el usuario de la base necesita permiso para crear bases de datos).

### 3.7 Comandos útiles

| Comando | Qué hace |
|---|---|
| `python manage.py migrate` | Crea o actualiza las tablas según las migraciones. |
| `python manage.py createsuperuser` | Crea un administrador (correo, nombre, contraseña). |
| `python manage.py runserver` | Servidor de desarrollo en el puerto 8000. |
| `python manage.py collectstatic` | Reúne CSS/JS/imágenes en `staticfiles/` (producción). |
| `python manage.py test` | Ejecuta las pruebas automáticas. |
| `python manage.py importar_usuarios archivo.csv` | Carga cuentas desde un CSV con columnas `correo, nombre, contrasena (hash), puntos, nivel, fecha_registro`. |

### 3.8 Despliegue en Render

Guía detallada: [`DESPLIEGUE_RENDER.md`](DESPLIEGUE_RENDER.md). En resumen:

1. El repositorio de GitHub debe tener `manage.py` y `build.sh` **en la raíz** (no dentro de otra carpeta).
2. En Render: **New → PostgreSQL** (plan Free) y copia su **Internal Database URL**.
3. **New → Web Service** → elige el repositorio y configura:

| Campo | Valor |
|---|---|
| Runtime | Python 3 |
| Build Command | `bash build.sh` |
| Start Command | `gunicorn config.wsgi:application` |
| Root Directory | *(vacío)* |

4. En **Environment** agrega: `PYTHON_VERSION=3.12.3`, `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<clave larga>`,
   `DATABASE_URL=<Internal Database URL>` y, si quieres un administrador inicial,
   `DJANGO_SUPERUSER_CORREO`, `DJANGO_SUPERUSER_NOMBRE`, `DJANGO_SUPERUSER_PASSWORD`.
5. Cada `git push` a la rama `main` vuelve a desplegar. (Alternativa: **New → Blueprint**, que lee `render.yaml`.)

**¿Qué hace `build.sh` en cada despliegue?**

1. `pip install -r requirements.txt` — instala las dependencias.
2. `python manage.py collectstatic --no-input` — reúne los archivos estáticos para WhiteNoise.
3. `python manage.py migrate --no-input` — crea o actualiza las tablas en PostgreSQL.
4. Si existe `DJANGO_SUPERUSER_CORREO`, crea el administrador (si ya existe, lo ignora y continúa).

> En el plan gratuito el servicio se **duerme** tras un rato sin visitas: la primera carga puede tardar unos
> segundos. Revisa en la página de precios de Render las condiciones vigentes del plan gratuito de PostgreSQL.

### 3.9 Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `No module named 'django'` | No activaste el entorno virtual o no instalaste las dependencias. | `venv\Scripts\activate` y `pip install -r requirements.txt`. |
| En PowerShell: *la ejecución de scripts está deshabilitada* | Política de PowerShell. | Usa **CMD**, o ejecuta `Set-ExecutionPolicy -Scope Process Bypass` y activa el entorno otra vez. |
| `no such table` / `relation … does not exist` | Faltan las tablas. | `python manage.py migrate`. |
| `Con DJANGO_DEBUG=0 debes definir DJANGO_SECRET_KEY` | Producción sin clave propia. | Define `DJANGO_SECRET_KEY`. |
| `Bad Request (400)` en producción | El dominio no está permitido. | `DJANGO_ALLOWED_HOSTS` (en Render se añade solo con `RENDER_EXTERNAL_HOSTNAME`). |
| `403 CSRF verification failed` con dominio propio | Falta el origen de confianza. | `DJANGO_CSRF_TRUSTED_ORIGINS=https://tu-dominio.com`. |
| `UnknownSchemeError: Scheme '://' is unknown` | `DATABASE_URL` mal copiada. | Debe empezar por `postgresql://` o `postgres://`; cópiala con el botón de Render, sin comillas ni espacios. |
| El sitio se ve sin estilos | Sin Internet (CDN) o, en producción, falta `collectstatic`. | Verifica la conexión; `build.sh` ya ejecuta `collectstatic`. |
| `/panel/` responde 404 | Tu cuenta no es superusuario (se oculta a propósito). | Crea una con `createsuperuser` o desde el panel. |
| No puedo iniciar sesión | El correo se guarda en minúsculas, o la cuenta está **suspendida**. | Escribe el correo en minúsculas; reactívala desde el panel. |
| El dump falla con `already exists` | La base ya tenía tablas (por `migrate`). | Vacía el esquema (ver 3.5) o usa una base nueva. |
| `psql` / `createdb` no se reconocen | No está el cliente de PostgreSQL. | Instala PostgreSQL (incluye el cliente) y reabre la terminal. |
| Render tarda en abrir | El plan gratuito entra en reposo. | Espera unos segundos y recarga. |

---

## 4. Cómo funciona el código

### 4.1 Idea general

Django organiza el código en **Modelo – Plantilla – Vista**. Cada vez que el navegador pide una página ocurre esto:

```
Navegador ──(1) petición HTTP──▶ config/urls.py ──(2) elige la vista──▶ views.py de una app
    ▲                                                                       │
    │                                              (3) consulta o guarda con el ORM
    │                                                                       ▼
    └─────────(5) HTML ◀──── plantilla (templates/) ◀──(4) datos──── models.py ⇄ Base de datos
```

1. `config/urls.py` es la **tabla de rutas**: según la dirección decide qué vista atiende.
2. La **vista** (`views.py`) aplica las reglas: ¿hay sesión?, ¿el formulario es válido?, ¿alcanzan los puntos?
3. Los **modelos** (`models.py`) representan las tablas; el ORM de Django evita escribir SQL a mano.
4. La **plantilla** (`.html`) recibe los datos y genera la página que ve el usuario.

### 4.2 Mapa del proyecto

```
ODS-14/
├── manage.py               # punto de entrada de todos los comandos de Django
├── requirements.txt        # dependencias de Python
├── build.sh · render.yaml  # despliegue en Render
├── .env.example            # lista de variables de entorno (sin valores reales)
├── config/                 # configuración global
│   ├── settings.py         #   ajustes: variables de entorno, base de datos, estáticos…
│   ├── urls.py             #   rutas principales
│   └── wsgi.py · asgi.py   #   entrada del servidor
├── core/                   # páginas educativas (inicio, aprende, juega, quiz, mares, actúa)
├── usuarios/               # cuentas, perfil, puntos, avatar y modelos de la tienda
├── tienda/                 # tienda de avatares (comprar y equipar partes)
├── panel/                  # panel exclusivo de superusuarios
├── templates/              # base.html (barra, franja de título, pie) y base_auth.html
├── static/                 # css/ · js/ · avatar/ (16 PNG) · plugins/ (Font Awesome, jQuery, Bootstrap JS)
└── database/               # schema.sql, dump con datos de ejemplo y diagramas entidad-relación
```

### 4.3 Las cuatro apps

| App | Responsabilidad | Archivos clave |
|---|---|---|
| **`core`** | Páginas informativas e interactivas. Casi no tiene lógica de servidor: las vistas solo muestran plantillas; el juego ocurre en el navegador. | `views.py` (una vista por página), `mixins.py` (`HeroMixin`), `templatetags/oceano.py` (burbujas animadas del login) |
| **`usuarios`** | Todo lo de la **cuenta**: modelo de usuario con correo como identificador, registro, login, perfil, puntos y avatar. Aquí viven los modelos de la tienda. | `models.py`, `forms.py`, `views.py`, `admin.py`, `templatetags/avatar.py`, `migrations/`, `management/commands/importar_usuarios.py` |
| **`tienda`** | Pantalla de la tienda y las acciones **comprar** y **equipar**. La lógica de negocio está en el modelo (`Usuario.comprar()`), no en la vista. | `views.py`, `urls.py`, `templates/tienda/tienda.html` |
| **`panel`** | Panel de administración propio, solo para superusuarios. | `mixins.py` (control de acceso), `views.py`, `forms.py`, `templates/panel/` |

### 4.4 Plantillas y archivos estáticos

- **`templates/base.html`** es la plantilla madre: barra de navegación (con el avatar y los puntos del usuario),
  franja azul de título, pie de página y la carga de CSS/JS. Las demás páginas la **extienden** y solo rellenan
  `{% block content %}`.
- **`HeroMixin`** (`core/mixins.py`) permite que cada vista declare su título, subtítulo e icono
  (`titulo`, `subtitulo`, `icono`), que `base.html` dibuja en la franja azul.
- **`base_auth.html`** es la plantilla independiente de *login* y *registro* (fondo azul con burbujas).
- **Etiqueta `{% avatar user 48 %}`** (`usuarios/templatetags/avatar.py`): dibuja el avatar apilando los PNG del usuario.
- **`static/css/mision-oceano.css`** contiene todos los estilos propios. Los PNG del avatar usan
  `image-rendering: pixelated` para verse nítidos al ampliarlos.
- **`static/js/mision-oceano.js`** concentra la interactividad, en funciones separadas:

| Función | Qué hace |
|---|---|
| `inicializarQuiz()` | Quiz de 5 preguntas; calcula 10 puntos por acierto y habilita *Guardar mis puntos*. |
| `inicializarMemoria()` | Memoria marina; puntos = `80 − 2 × intentos` (mínimo 20); guarda sola al terminar. |
| `inicializarRecolector()` | Juego en `<canvas>`; restar 5 puntos al atrapar un animal; guarda el puntaje final (máximo 100). |
| `inicializarChecklistActua()` | Compromisos de *Actúa*; se guardan en el `localStorage` del navegador (no en la base de datos). |
| `guardarPuntos()` | Envía los puntos al servidor y actualiza los contadores de la página. |

- En producción **WhiteNoise** sirve los archivos estáticos (`collectstatic` los reúne en `staticfiles/`);
  en desarrollo los sirve `runserver`.

### 4.5 Modelo de datos

Tres tablas propias (en `usuarios/models.py`) más las tablas de soporte que crea Django
(permisos, sesiones, bitácora del admin…). El diagrama completo está en [`database/`](#5-base-de-datos-y-diagramas).

| Modelo (tabla) | Qué guarda | Campos principales |
|---|---|---|
| **`Usuario`** (`usuarios_usuario`) | La cuenta. El **correo** es el identificador de inicio de sesión. | `correo` (único), `nombre`, `password` (hash), `puntos`, `puntos_gastados`, `nivel`, `fecha_registro`, `is_active`, `is_staff`, `is_superuser` y cinco llaves a la parte puesta: `avatar_base`, `avatar_cara`, `avatar_pelo`, `avatar_camisa`, `avatar_pantalon`. |
| **`ParteAvatar`** (`usuarios_parteavatar`) | Catálogo: una fila por cada PNG del avatar. | `categoria`, `numero`, `nombre`, `precio`, `archivo`. Único por (`categoria`, `numero`). **Precio 0 = gratis para todos.** |
| **`ParteAdquirida`** (`usuarios_parteadquirida`) | Historial de compras: qué usuario compró qué parte. | `usuario`, `parte`, `precio_pagado`, `fecha`. Único por (`usuario`, `parte`). |

Las migraciones (`usuarios/migrations/`) son el historial versionado del esquema: `0001` crea el usuario,
`0002` añade avatar y tienda, y `0003` **carga el catálogo inicial** de 16 partes. Por eso un simple `migrate`
deja el sistema listo.

### 4.6 Reglas de negocio

**Puntos, nivel e insignias**

- `puntos` es el **total ganado** y nunca baja. El **nivel** sale de él: `nivel = puntos // 100 + 1`.
- Las **insignias** se desbloquean con el total ganado: 0, 50, 150 y 300 puntos.
- Lo que se gasta en la tienda se acumula en `puntos_gastados`. Los **puntos disponibles** son
  `puntos − puntos_gastados`; es el número que muestra la barra. Así, comprar **no baja el nivel ni quita insignias**.

**Avatar por capas**

- El avatar son 5 PNG de 160×160 apilados en este orden: **base → cara → pelo → camisa → pantalón**.
  El orden está en `CategoriaAvatar` (`usuarios/models.py`): reordenar esas líneas cambia las capas.
- Las partes con número **0** son gratis y todo usuario nuevo las tiene. Si una categoría está vacía,
  se usa la parte gratuita de menor número (`Usuario.avatar_equipado()`, que hace una sola consulta).
- Los precios iniciales (pelo 60–120, camisa y pantalón 40–60) se cambian en **`/admin/` → Partes de avatar**.

**La compra** vive en `Usuario.comprar()` y es atómica: bloquea la fila del usuario para que dos compras
simultáneas no gasten dos veces los mismos puntos.

```python
def comprar(self, parte):
    with transaction.atomic():
        fila = type(self).objects.select_for_update().get(pk=self.pk)     # bloquea la fila
        parte = ParteAvatar.objects.get(pk=parte.pk)                      # precio vigente
        if parte.precio == 0 or ParteAdquirida.objects.filter(usuario=fila, parte=parte).exists():
            raise ErrorTienda(f'Ya tienes «{parte.nombre}».')
        if fila.puntos_disponibles < parte.precio:
            raise ErrorTienda(f'Te faltan {parte.precio - fila.puntos_disponibles} puntos …')
        ParteAdquirida.objects.create(usuario=fila, parte=parte, precio_pagado=parte.precio)
        fila.puntos_gastados += parte.precio
        setattr(fila, f'avatar_{parte.categoria}', parte)                 # se estrena puesta
        fila.save(update_fields=['puntos_gastados', f'avatar_{parte.categoria}'])
```

### 4.7 Flujos paso a paso

**Registro e inicio de sesión** (`usuarios/forms.py`, `usuarios/views.py`)
1. `RegistroForm` valida en orden: campos completos → correo válido → nombre ≤ 60 caracteres →
   contraseñas iguales → mínimo 6 caracteres → correo no repetido. Muestra un solo mensaje de error.
2. Si todo es válido crea el usuario (correo en minúsculas, contraseña con hash) e **inicia sesión sola**.
3. `LoginView` autentica con correo y contraseña. Respeta `?next=` (solo si apunta al mismo sitio) y
   un usuario **suspendido** no puede entrar. Cerrar sesión es un `POST` (con CSRF).

**Ganar puntos** (`static/js/mision-oceano.js` → `usuarios/views.py`)
1. Al terminar una actividad, el JS llama a `guardarPuntos(puntos)`.
2. Hace un `POST` a `/guardar-puntos/` con el token CSRF (leído de `<meta name="csrf-token">`).
   La URL viene de `<body data-url-guardar-puntos>`, que solo existe si hay sesión.
3. La vista `guardar_puntos` exige sesión y `POST`, acota los puntos entre 1 y 100 y llama a `sumar_puntos()`,
   que suma y recalcula el nivel dentro de una transacción.
4. Responde JSON, p. ej. `{"ok": true, "puntos": 150, "disponibles": 110, "nivel": 2}`, y el JS
   actualiza los contadores sin recargar la página.

**Comprar una parte** (`tienda/views.py`)
1. `TiendaView` agrupa el catálogo por pestañas (`?categoria=pelo|camisa|pantalon`); solo aparecen las categorías
   con más de una opción. Cada tarjeta dibuja **tu avatar con esa parte puesta** (`avatar_probando`).
2. Según el estado muestra **Ponértela** (ya es tuya o es gratis), **Comprar · N** (alcanzan los puntos) o
   **bloqueada** con los puntos que faltan.
3. `ComprarView` / `EquiparView` aceptan solo `POST` con CSRF, llaman a `request.user.comprar(parte)` o `.equipar(parte)`,
   guardan un mensaje de éxito o de error y redirigen a la misma pestaña.

**Administración de cuentas** (`/panel/`, app `panel`)
- **Acceso:** sin sesión → login; con sesión pero sin ser superusuario → **404**, para no revelar que existe.
- **Resumen:** totales de cuentas, activas, suspendidas, superusuarios, registros de los últimos 7 días,
  puntos acumulados y las cuentas más recientes.
- **Usuarios:** búsqueda por nombre o correo, filtros por estado y tipo, paginación; crear cuentas
  (crear un superusuario pide **tu contraseña**), **suspender** (cierra sus sesiones), **reactivar** y **eliminar**
  (con pantalla de confirmación).
- **Protecciones:** no puedes suspender ni eliminar tu propia cuenta y siempre debe quedar **al menos un
  superusuario activo**.
- **Base de datos:** explorador de **solo lectura**: lista las tablas con su número de columnas y filas, y muestra
  sus registros. Las columnas sensibles (`password`, `session_key`, `session_data`) se enmascaran.

### 4.8 Seguridad

- **Contraseñas con hash** (PBKDF2 de Django); nunca se guardan en texto plano.
- **Protección CSRF** en todos los formularios y en las peticiones `fetch` del JS.
- **ORM de Django** (consultas parametrizadas) en lugar de SQL escrito a mano.
- **Control de acceso:** `@login_required`/`LoginRequiredMixin` en perfil y tienda; panel solo para superusuarios.
- **Redirecciones seguras:** `?next=` solo se acepta si apunta al mismo sitio.
- **Integridad en la base de datos:** llaves foráneas, restricciones `UNIQUE` y `CHECK` (por ejemplo, puntos ≥ 0).
- **Producción:** con `DJANGO_DEBUG=0` se activan cookies seguras y confianza en el proxy HTTPS de Render, y el
  proyecto **se niega a arrancar** con la clave secreta de ejemplo.

### 4.9 Configuración (`config/settings.py`)

- Lee un archivo `.env` con una función propia (sin librerías externas) y luego las variables de entorno.
- **Base de datos:** `DATABASE_URL` (PostgreSQL) → MySQL → SQLite, como se explicó en 3.4.
- **Usuario propio:** `AUTH_USER_MODEL = 'usuarios.Usuario'`; la contraseña debe tener al menos 6 caracteres.
- **Zona horaria y idioma:** `America/Bogota`, `es-co`.
- **Estáticos:** carpeta `static/` como origen, `staticfiles/` como destino de `collectstatic`, WhiteNoise como servidor.

### 4.10 Pruebas automáticas

Hay pruebas en `core/`, `usuarios/` (`tests.py`, `test_avatar.py`), `tienda/` y `panel/`. Cubren, entre otras cosas:

- todas las páginas responden y marcan la sección activa;
- registro, login, logout, `?next=` y cambio de nombre, con los mismos mensajes de error que ve el usuario;
- `guardar_puntos` (límites, sesión y CSRF), nivel e insignias;
- compras: saldo, no comprar dos veces, precio vigente y que dos pestañas con datos viejos no gasten dos veces;
- permisos del panel y reglas de suspender, eliminar y crear cuentas;
- el avatar por capas y que el catálogo apunte a PNG que existen.

---

## 5. Base de datos y diagramas

La carpeta [`database/`](database/) reúne lo necesario para entender y restaurar la base de datos:

| Archivo | Contenido |
|---|---|
| `schema.sql` | Script SQL (PostgreSQL) con **todas las tablas**, tipos, llaves primarias y foráneas, restricciones e índices. |
| `mision_oceano_dump.sql` | Copia de respaldo **con datos de ejemplo** (catálogo, 10 usuarios, 25 compras). Ver 3.5. |
| `diagrama_er.png` | Diagrama entidad-relación completo (las 12 tablas) en alta resolución. |
| `diagrama_er_negocio.png` | Diagrama enfocado en las 3 tablas propias (`Usuario`, `ParteAvatar`, `ParteAdquirida`). |

Para crear la base **solo con la estructura** (sin datos): `psql -d mision_oceano -f database/schema.sql`.
El esquema coincide exactamente con el que generan las migraciones de Django.

