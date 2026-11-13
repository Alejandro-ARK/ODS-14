"""
Carga el banco inicial de preguntas del reto en vivo (incluye las 5 del quiz de /quiz/,
ahora con 4 opciones) y crea el grupo «Docentes» (RF-01).

Las opciones se guardan en orden aleatorio (con semilla fija) para que el id de la opción
correcta no delate cuál es: el cliente recibe ids, nunca la marca de «correcta».
"""
import random

from django.db import migrations

# (tema, enunciado, opción correcta, [distractores])
BANCO = [
    ('ODS 14', '¿Qué busca el ODS 14 «Vida submarina»?',
     'Conservar y usar de forma sostenible los océanos, los mares y los recursos marinos',
     ['Aumentar la pesca industrial sin límites', 'Construir más puertos en zonas de manglar',
      'Extraer petróleo en todos los arrecifes']),
    ('ODS 14', '¿Qué busca la meta 14.1 del ODS 14?',
     'Reducir la contaminación marina, en especial la que viene de actividades en tierra',
     ['Construir más barcos pesqueros', 'Aumentar el turismo en los arrecifes', 'Prohibir nadar en el mar']),
    ('ODS 14', '¿Qué día se celebra el Día Mundial de los Océanos?',
     '8 de junio', ['22 de abril', '5 de junio', '16 de septiembre']),
    ('ODS 14', '¿Para qué sirven las áreas marinas protegidas?',
     'Para conservar ecosistemas y dejar que las especies se recuperen',
     ['Para construir hoteles sin permisos', 'Para pescar sin ningún control', 'Para botar residuos lejos de la costa']),
    ('Ecosistemas', '¿Qué porcentaje aproximado de las especies marinas depende de los arrecifes de coral?',
     'Cerca del 25 %', ['5 %', '60 %', '90 %']),
    ('Ecosistemas', '¿Qué función cumplen los manglares?',
     'Protegen la costa de la erosión y son guardería de especies jóvenes',
     ['No cumplen ninguna función ecológica', 'Solo sirven como madera de construcción',
      'Calientan el agua del mar']),
    ('Ecosistemas', '¿Qué parte de la superficie de la Tierra cubren los océanos?',
     'Cerca del 71 %', ['Cerca del 30 %', 'La mitad exacta', 'Más del 95 %']),
    ('Ecosistemas', '¿Qué organismos microscópicos producen cerca de la mitad del oxígeno del planeta?',
     'El fitoplancton', ['Las medusas', 'Los tiburones', 'Los cangrejos']),
    ('Ecosistemas', '¿Qué gas absorbe el océano en grandes cantidades, ayudando a regular el clima?',
     'Dióxido de carbono (CO₂)', ['Helio', 'Neón', 'Hidrógeno']),
    ('Amenazas', '¿Qué es la acidificación del océano?',
     'La baja del pH del agua de mar al absorber CO₂',
     ['El aumento de la sal por la evaporación', 'La llegada de agua dulce de los ríos',
      'Que el mar se vuelva más frío']),
    ('Amenazas', '¿Qué son los microplásticos?',
     'Fragmentos de plástico de menos de 5 mm',
     ['Plásticos que se disuelven en el agua', 'Algas de color plateado', 'Peces muy pequeños']),
    ('Amenazas', '¿Qué causa el blanqueamiento de los corales?',
     'El agua más caliente, que hace que el coral expulse las algas que viven en él',
     ['La luz de la luna llena', 'El exceso de peces en el arrecife', 'La sal del mar']),
    ('Amenazas', '¿Qué es la pesca incidental?',
     'Capturar especies que no eran el objetivo, como tortugas o delfines',
     ['Pescar solo los fines de semana', 'Pescar con caña desde la playa', 'Pescar en un acuario']),
    ('Amenazas', '¿Qué es la sobrepesca?',
     'Pescar más rápido de lo que las poblaciones logran reponerse',
     ['Pescar solo peces grandes', 'Pescar con redes de colores', 'Pescar en ríos en vez del mar']),
    ('Amenazas', '¿Por qué las tortugas marinas se comen las bolsas plásticas?',
     'Porque flotando se parecen a las medusas',
     ['Porque tienen sabor dulce', 'Porque les ayudan a respirar', 'Porque las usan para hacer nidos']),
    ('Amenazas', '¿Cuál de estos residuos tarda más en degradarse en el mar?',
     'Una botella de plástico', ['Una cáscara de banano', 'Un periódico', 'Un corazón de manzana']),
    ('Nuestros mares', '¿Con cuántos mares u océanos tiene costa Colombia?',
     'Dos: el océano Pacífico y el mar Caribe', ['Uno', 'Tres', 'Cuatro']),
    ('Nuestros mares', '¿Qué isla colombiana del Pacífico es Patrimonio de la Humanidad y famosa por sus tiburones martillo?',
     'Malpelo', ['San Andrés', 'Providencia', 'Isla Fuerte']),
    ('Nuestros mares', '¿Dónde queda la Reserva de Biosfera Seaflower?',
     'En el archipiélago de San Andrés, Providencia y Santa Catalina',
     ['En la bahía de Buenaventura', 'En el golfo de Urabá', 'En la isla Gorgona']),
    ('Nuestros mares', '¿Para qué llegan las ballenas jorobadas al Pacífico colombiano?',
     'Para aparearse y tener sus crías en aguas cálidas',
     ['Para hibernar en el fondo del mar', 'Para comer plástico', 'Para cambiar de piel']),
    ('Nuestros mares', '¿Qué especie invasora afecta los arrecifes del Caribe colombiano?',
     'El pez león', ['El pargo rojo', 'El mero', 'El caballito de mar']),
    ('Acciones', '¿Cuál de estas acciones ayuda a cuidar el océano?',
     'Reducir el uso de plásticos de un solo uso',
     ['Botar basura en la playa', 'Pescar especies en veda', 'Arrojar aceite usado al desagüe']),
    ('Acciones', '¿Qué es una veda de pesca?',
     'Un periodo en que se prohíbe pescar una especie para que se reproduzca',
     ['Una red de pesca muy grande', 'Un concurso de pesca', 'Un tipo de anzuelo']),
]


def cargar(apps, schema_editor):
    Pregunta = apps.get_model('vivo', 'Pregunta')
    Opcion = apps.get_model('vivo', 'Opcion')
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Docentes')

    azar = random.Random(14)
    for tema, enunciado, correcta, distractores in BANCO:
        pregunta = Pregunta.objects.create(tema=tema, enunciado=enunciado)
        opciones = [(correcta, True)] + [(d, False) for d in distractores]
        azar.shuffle(opciones)
        Opcion.objects.bulk_create(Opcion(pregunta=pregunta, texto=t, correcta=c) for t, c in opciones)


def deshacer(apps, schema_editor):
    apps.get_model('vivo', 'Pregunta').objects.filter(enunciado__in=[b[1] for b in BANCO]).delete()
    apps.get_model('auth', 'Group').objects.filter(name='Docentes').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('vivo', '0001_inicial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [migrations.RunPython(cargar, deshacer)]
