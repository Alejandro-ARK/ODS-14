"""
Carga el catálogo inicial de partes del avatar (los 16 PNG de static/avatar/).

Las partes con número 0 son gratuitas y las tiene todo el mundo desde que se registra;
el resto se compran en la tienda. Los precios y nombres se pueden cambiar después desde
el panel /admin/ → "Partes de avatar" (esta migración solo corre una vez).
"""
from django.db import migrations

# (categoría, número, nombre, precio)
CATALOGO = [
    ('base',     0, 'Base',                    0),

    ('cara',     0, 'Cara clásica',            0),

    ('pelo',     0, 'Corto con broche',        0),
    ('pelo',     1, 'Media melena con broche', 60),
    ('pelo',     2, 'Voluminoso',              100),
    ('pelo',     3, 'Coleta larga',            80),
    ('pelo',     4, 'Pinchos',                 120),
    ('pelo',     5, 'Largo con flequillo',     80),

    ('camisa',   0, 'Camiseta verde',          0),
    ('camisa',   1, 'Camiseta azul',           40),
    ('camisa',   2, 'Camiseta roja',           40),
    ('camisa',   3, 'Camiseta rosa',           60),

    ('pantalon', 0, 'Pantalón azul',           0),
    ('pantalon', 1, 'Pantalón morado',         40),
    ('pantalon', 2, 'Pantalón azul noche',     40),
    ('pantalon', 3, 'Pantalón blanco',         60),
]

# Los PNG se llaman Base_Avatar0.png, Base_Avatar_Pelo1.png, Base_Avatar_Camisa2.png…
NOMBRE_ARCHIVO = {
    'base': 'Base_Avatar{n}.png',
    'cara': 'Base_Avatar_Cara{n}.png',
    'pelo': 'Base_Avatar_Pelo{n}.png',
    'camisa': 'Base_Avatar_Camisa{n}.png',
    'pantalon': 'Base_Avatar_Pantalon{n}.png',
}


def cargar_catalogo(apps, schema_editor):
    ParteAvatar = apps.get_model('usuarios', 'ParteAvatar')
    for categoria, numero, nombre, precio in CATALOGO:
        ParteAvatar.objects.update_or_create(
            categoria=categoria, numero=numero,
            defaults={
                'nombre': nombre,
                'precio': precio,
                'archivo': 'avatar/' + NOMBRE_ARCHIVO[categoria].format(n=numero),
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_avatar_y_tienda'),
    ]

    operations = [
        # Al revertir no se borra nada: el esquema (0002) se encarga de eliminar la tabla.
        migrations.RunPython(cargar_catalogo, migrations.RunPython.noop),
    ]
