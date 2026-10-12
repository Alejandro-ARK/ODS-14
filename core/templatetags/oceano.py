import random

from django import template

register = template.Library()


@register.inclusion_tag('core/partials/burbujas.html')
def burbujas(cantidad=14):
    """Burbujas animadas del fondo de login/registro (tamaño y posición al azar)."""
    return {
        'burbujas': [
            {
                'tam': random.randint(10, 36),
                'izq': random.randint(0, 100),
                'duracion': random.randint(7, 16),
                'retraso': random.randint(0, 10),
            }
            for _ in range(cantidad)
        ]
    }
