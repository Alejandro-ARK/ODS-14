"""
Configuración de Misión Océano.

Los valores sensibles o que cambian entre equipos (clave secreta, base de
datos, modo debug) se leen de variables de entorno o de un archivo ".env"
en la raíz del proyecto. Mira ".env.example" para ver cuáles existen.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env(ruta):
    """Carga un archivo .env sencillo (CLAVE=valor) sin dependencias externas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, valor = linea.split('=', 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
_CLAVE_DE_DESARROLLO = 'django-insecure-solo-para-desarrollo-cambiala-en-produccion'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', _CLAVE_DE_DESARROLLO)
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

# Render define RENDER_EXTERNAL_HOSTNAME (p. ej. mision-oceano.onrender.com)
_host_render = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]
if _host_render:
    ALLOWED_HOSTS.append(_host_render)
    CSRF_TRUSTED_ORIGINS.append(f'https://{_host_render}')

if not DEBUG and SECRET_KEY == _CLAVE_DE_DESARROLLO:
    raise ImproperlyConfigured(
        'Con DJANGO_DEBUG=0 debes definir DJANGO_SECRET_KEY con una clave propia.'
    )

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'daphne',     # servidor ASGI (HTTP + WebSockets); debe ir PRIMERO para que runserver lo use
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps del proyecto
    'core',       # páginas educativas: inicio, aprende, juega, quiz, mares, actúa
    'usuarios',   # cuentas, perfil y puntos
    'panel',      # panel de administración exclusivo para superusuarios
    'tienda',     # tienda de avatares: se compran partes con los puntos
    'channels',   # WebSockets (Django Channels)
    'vivo',       # reto multijugador en vivo con QR dinámico
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # sirve los estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # base.html y base_auth.html
        'APP_DIRS': True,                   # plantillas dentro de cada app
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'   # Daphne: HTTP + WebSockets del reto en vivo

# ---------------------------------------------------------------------------
# Capa de canales (difunde los eventos del reto a todos los participantes)
#   - Con REDIS_URL (Render Key Value o Upstash) usa Redis: obligatorio en producción.
#   - Sin REDIS_URL usa memoria: sirve solo en desarrollo, con un único proceso.
# ---------------------------------------------------------------------------
if os.environ.get('REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            # socket_timeout > 5 s: desde redis-py 8 el límite por defecto es 5 s, igual a la espera
            # interna de channels-redis, y las conexiones se cortaban con «Timeout reading from».
            'CONFIG': {'hosts': [{'address': os.environ['REDIS_URL'], 'socket_timeout': 30}]},
        },
    }
else:
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}

# ---------------------------------------------------------------------------
# Base de datos
#   - Por defecto usa SQLite (no requiere instalar nada).
#   - Con DB_ENGINE=mysql usa MySQL/MariaDB (el mismo motor que phpMyAdmin).
# ---------------------------------------------------------------------------
if os.environ.get('DATABASE_URL'):
    # Render entrega la base PostgreSQL como una sola URL.
    import dj_database_url
    # Con ASGI (Daphne) cada hilo abriría su propia conexión persistente y se agotaría el
    # límite del plan gratuito; por eso por defecto se cierra la conexión tras cada uso.
    DATABASES = {'default': dj_database_url.config(
        conn_max_age=int(os.environ.get('DB_CONN_MAX_AGE', '0')), conn_health_checks=True)}
elif os.environ.get('DB_ENGINE', 'sqlite') == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'mision_oceano_django'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'core:inicio'
LOGOUT_REDIRECT_URL = 'core:inicio'

# El sitio PHP exigía mínimo 6 caracteres; se mantiene esa regla.
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
]

# Los hashes generados con password_hash() de PHP son bcrypt. Al listar
# BCryptPasswordHasher, Django los acepta tal cual y, la primera vez que el
# usuario inicia sesión, los convierte automáticamente al hasher preferido
# (el primero de la lista). Requiere el paquete "bcrypt".
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos (CSS, JS, Font Awesome)
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'   # destino de "collectstatic" en producción
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# ---------------------------------------------------------------------------
# Producción (DJANGO_DEBUG=0): Render termina el HTTPS y reenvía a la app por HTTP
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
