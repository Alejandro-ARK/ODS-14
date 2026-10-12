"""
Importa a la base de datos de Django los usuarios del sitio PHP original.

Pasos:
  1. En phpMyAdmin abre la tabla `usuarios` -> Exportar -> formato CSV.
     Marca la casilla "Poner los nombres de las columnas en la primera línea".
  2. Ejecuta:   python manage.py importar_usuarios usuarios.csv

Las contraseñas NO hay que restablecerlas: PHP las guardó con password_hash()
(bcrypt, prefijo "$2y$") y aquí se convierten al formato de Django
("bcrypt$$2b$..."), de modo que cada persona entra con su clave de siempre. En
su primer inicio de sesión Django las actualiza solo a su algoritmo por defecto.

Columnas esperadas: correo, nombre, contrasena, puntos, nivel, fecha_registro
(la columna `id` y cualquier otra se ignoran).
"""
import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from usuarios.models import Usuario

COLUMNAS_OBLIGATORIAS = {'correo', 'nombre', 'contrasena'}
PREFIJOS_BCRYPT = ('$2y$', '$2a$', '$2b$')


def convertir_hash_php(hash_php):
    """'$2y$10$...' (PHP) -> 'bcrypt$$2b$10$...' (Django). None si no es bcrypt."""
    hash_php = (hash_php or '').strip()
    if len(hash_php) != 60 or not hash_php.startswith(PREFIJOS_BCRYPT):
        return None
    return 'bcrypt$' + '$2b$' + hash_php[4:]


def a_entero(valor, por_defecto):
    try:
        return max(0, int(str(valor).strip()))
    except (TypeError, ValueError):
        return por_defecto


def a_fecha(valor):
    valor = (valor or '').strip()
    if not valor or valor.upper() == 'NULL':
        return timezone.now()
    try:
        return timezone.make_aware(datetime.strptime(valor, '%Y-%m-%d %H:%M:%S'))
    except ValueError:
        return timezone.now()


class Command(BaseCommand):
    help = 'Importa usuarios desde un CSV exportado de la tabla `usuarios` del sitio PHP.'

    def add_arguments(self, parser):
        parser.add_argument('archivo_csv', help='Ruta del CSV exportado desde phpMyAdmin.')
        parser.add_argument('--delimitador', default=',', help='Separador del CSV (por defecto ",").')

    def handle(self, *args, archivo_csv, delimitador, **opciones):
        try:
            # utf-8-sig tolera el BOM que algunos exportadores añaden al inicio.
            f = open(archivo_csv, newline='', encoding='utf-8-sig')
        except OSError as e:
            raise CommandError(f'No se pudo abrir el archivo: {e}')

        with f:
            lector = csv.DictReader(f, delimiter=delimitador)
            faltan = COLUMNAS_OBLIGATORIAS - set(lector.fieldnames or [])
            if faltan:
                raise CommandError(
                    'El CSV no tiene las columnas: ' + ', '.join(sorted(faltan)) +
                    '. ¿Marcaste "Poner los nombres de las columnas en la primera línea" al exportar?'
                )

            creados = omitidos = 0
            for n, fila in enumerate(lector, start=2):   # la fila 1 es el encabezado
                correo = (fila.get('correo') or '').strip().lower()
                nombre = (fila.get('nombre') or '').strip()[:60]
                clave = convertir_hash_php(fila.get('contrasena'))

                if not correo or not nombre:
                    self.stdout.write(self.style.WARNING(f'Fila {n}: sin correo o nombre; se omite.'))
                    omitidos += 1
                    continue
                if clave is None:
                    self.stdout.write(self.style.WARNING(
                        f'Fila {n} ({correo}): la contraseña no es un hash bcrypt de PHP; se omite.'))
                    omitidos += 1
                    continue
                if Usuario.objects.filter(correo__iexact=correo).exists():
                    self.stdout.write(f'Fila {n} ({correo}): ya existe; se omite.')
                    omitidos += 1
                    continue

                puntos = a_entero(fila.get('puntos'), 0)
                Usuario.objects.create(
                    correo=correo,
                    nombre=nombre,
                    password=clave,   # ya viene hasheado: no se pasa por set_password()
                    puntos=puntos,
                    nivel=a_entero(fila.get('nivel'), Usuario.calcular_nivel(puntos)) or 1,
                    fecha_registro=a_fecha(fila.get('fecha_registro')),
                )
                creados += 1

        self.stdout.write(self.style.SUCCESS(f'Listo: {creados} usuario(s) importado(s), {omitidos} omitido(s).'))
