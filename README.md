# 🌊 Misión Océano — versión Django

Migración del sitio PHP/MySQL (phpMyAdmin) a Django. Mismo diseño, mismas páginas,
mismos textos y mismas reglas de puntos y niveles.

## Puesta en marcha

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser      # pedirá correo, nombre y contraseña
python manage.py runserver
```

Abre <http://127.0.0.1:8000/> · panel de administración en <http://127.0.0.1:8000/admin/>.

Por defecto usa **SQLite** (no requiere instalar nada). Para seguir con **MySQL** (XAMPP/phpMyAdmin):

1. Crea una base vacía en phpMyAdmin, p. ej. `mision_oceano_django` (cotejamiento `utf8mb4_unicode_ci`).
2. `pip install mysqlclient`
3. Copia `.env.example` a `.env`, pon `DB_ENGINE=mysql` y los datos de conexión.
4. `python manage.py migrate`

> Usa una base **nueva**: Django crea sus propias tablas (`usuarios_usuario`, `django_session`, …)
> y no debe compartir la base del sitio PHP.

## Traer los usuarios del sitio PHP

1. phpMyAdmin → base `mision_oceano` → tabla `usuarios` → **Exportar** → formato **CSV**,
   marcando *"Poner los nombres de las columnas en la primera línea"*.
2. `python manage.py importar_usuarios usuarios.csv`

Conserva correo, nombre, puntos, nivel y fecha de registro. **Las contraseñas no se restablecen**:
los hashes `password_hash()` de PHP (bcrypt) se convierten al formato de Django y cada persona
entra con su clave de siempre. Es seguro ejecutarlo varias veces (omite correos ya existentes).

## Estructura

```
config/            settings.py, urls.py, wsgi/asgi
core/              páginas educativas (inicio, aprende, juega, quiz, mares, actúa)
  views.py  mixins.py  urls.py  templatetags/oceano.py (burbujas del login)
  templates/core/  index, aprende, juega, quiz, mares, actua
usuarios/          cuentas, perfil y puntos
  models.py        Usuario (correo + nombre + puntos + nivel), lógica de nivel e insignias
  forms.py         login, registro, perfil (mismos mensajes de error que el PHP)
  views.py         login, registro, perfil, guardar_puntos (JSON)
  management/commands/importar_usuarios.py
templates/         base.html (navbar + hero + footer) y base_auth.html (login/registro)
static/            css/mision-oceano.css, js/mision-oceano.js, jQuery, Bootstrap JS, Font Awesome
```

### Equivalencias PHP → Django

| PHP | Django |
|---|---|
| `layout/header.php` + `footer.php` | `templates/base.html` |
| `$page_titulo`, `$hero_*` | atributos de la vista (`core/views.py`, `HeroMixin`) |
| `index.php`, `aprende.php`, … | `core/templates/core/*.html` |
| `login.php`, `register.php` | `usuarios/views.py` (`LoginView`, `RegistroView`) |
| `perfil.php` | `PerfilView` |
| `guardar_puntos.php` | `/guardar-puntos/` (`usuarios.views.guardar_puntos`) |
| `logout.php` | `/logout/` (solo POST) |
| `app/config.php` (PDO) | `config/settings.py` + `.env` |
| tabla `usuarios` | modelo `usuarios.Usuario` |
| `public/` (AdminLTE + plugins) | `static/` (solo lo que el sitio realmente usa) |
| carpeta `admin/` (vacía) | `/admin/` de Django, ya funcional |

## Pruebas

```bash
python manage.py test        # 30 pruebas
```

## Producción (resumen)

Define `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` (clave propia) y `DJANGO_ALLOWED_HOSTS`;
ejecuta `python manage.py collectstatic` y sirve `staticfiles/` desde el servidor web
(o añade WhiteNoise). Con `DEBUG=0` el proyecto se niega a arrancar con la clave de ejemplo.

## Desplegar en Render

Ver la guía en `DESPLIEGUE_RENDER.md`.
