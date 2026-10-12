#!/usr/bin/env bash
# Script de construcción para Render: se ejecuta en cada despliegue.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Crea el administrador la primera vez (si definiste las variables en Render).
# Si ya existe, el comando falla de forma inofensiva y el despliegue continúa.
if [[ -n "${DJANGO_SUPERUSER_CORREO:-}" ]]; then
  python manage.py createsuperuser --no-input || true
fi
