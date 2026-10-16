from django import template

register = template.Library()

# Tamaños que escalan el pixel art (160 px = 32 "píxeles" de 5 px) sin deformarlo:
#   completo → conviene 160, 192, 224, 256…  (múltiplos de 32)
#   busto    → conviene 48, 72, 96…           (múltiplos de 24)


@register.inclusion_tag('usuarios/partials/avatar.html')
def avatar(usuario, tamano=48, modo='busto', clase=''):
    """
    Dibuja el avatar del usuario apilando sus PNG.

        {% avatar user 48 %}                      → cabeza y hombros, para la barra de navegación
        {% avatar user 192 'completo' %}          → cuerpo entero
    """
    return {
        'capas': usuario.capas_avatar(),
        'tamano': tamano,
        'modo': modo,
        'clase': clase,
        'etiqueta': f'Avatar de {usuario.nombre}',
    }


@register.inclusion_tag('usuarios/partials/avatar.html')
def avatar_probando(usuario, parte, tamano=160, modo='completo', clase=''):
    """El avatar del usuario, pero llevando puesta `parte` (vista previa en la tienda)."""
    return {
        'capas': usuario.capas_avatar(probando=parte),
        'tamano': tamano,
        'modo': modo,
        'clase': clase,
        'etiqueta': f'Así te verías con {parte.nombre}',
    }
