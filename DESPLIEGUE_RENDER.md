# Desplegar Misión Océano en Render

Archivos ya preparados: `build.sh`, `render.yaml`, `requirements.txt` (gunicorn, WhiteNoise,
dj-database-url, psycopg) y `config/settings.py` (lee `DATABASE_URL`, `RENDER_EXTERNAL_HOSTNAME`).

> En Render el disco es efímero: **SQLite no sirve** (se borraría en cada despliegue).
> Por eso se usa PostgreSQL. Las tablas se crean solas con `migrate` en cada despliegue.

## 1. Sube el proyecto a GitHub
```bash
git init
git add .
git commit -m "Misión Océano en Django"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/mision-oceano.git
git push -u origin main
```
(`.gitignore` ya excluye `.env`, `db.sqlite3` y `venv/`.)

## 2a. Opción rápida: Blueprint
1. En <https://dashboard.render.com> → **New → Blueprint** → elige tu repositorio.
2. Render lee `render.yaml` y crea la base PostgreSQL y el servicio web.
3. Te pedirá los valores de `DJANGO_SUPERUSER_CORREO`, `DJANGO_SUPERUSER_NOMBRE` y
   `DJANGO_SUPERUSER_PASSWORD`: escribe los del administrador que quieres.
4. **Apply** y espera a ver "Your service is live".

## 2b. Opción manual
1. **New → PostgreSQL** (plan Free) → al crearse, copia la **Internal Database URL**.
2. **New → Web Service** → tu repositorio, y configura:

| Campo | Valor |
|---|---|
| Runtime | Python 3 |
| Build Command | `bash build.sh` |
| Start Command | `gunicorn config.wsgi:application` |

3. En **Environment** añade:

| Variable | Valor |
|---|---|
| `PYTHON_VERSION` | `3.12.3` |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | una clave larga y aleatoria (Render puede generarla) |
| `DATABASE_URL` | la Internal Database URL del paso 1 |
| `DJANGO_SUPERUSER_CORREO` | correo del administrador |
| `DJANGO_SUPERUSER_NOMBRE` | nombre del administrador |
| `DJANGO_SUPERUSER_PASSWORD` | contraseña del administrador |

## 3. Importar los usuarios del sitio PHP (opcional)
El plan gratuito no incluye terminal (Shell). Alternativas: usar una instancia de pago, o ejecutar
el comando desde tu computador apuntando a la base de Render con su **External Database URL**:
```bash
set DATABASE_URL=postgres://...External...      # Windows  (Linux/Mac: export DATABASE_URL=...)
python manage.py importar_usuarios usuarios.csv
```

## Cosas a saber
- El plan gratuito del servicio web se **duerme tras ~15 min sin visitas**; la primera carga
  después tarda unos segundos.
- La base PostgreSQL gratuita **tiene fecha de vencimiento**; revisa las condiciones actuales
  en la página de precios de Render y haz copias si guardas datos importantes.
- Cada `git push` a `main` vuelve a desplegar automáticamente.
- Si el sitio responde "Bad Request (400)", falta el dominio en `ALLOWED_HOSTS`
  (en Render se añade solo con `RENDER_EXTERNAL_HOSTNAME`; para un dominio propio usa
  `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`).
