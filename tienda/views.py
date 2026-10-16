from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from core.mixins import HeroMixin
from usuarios.models import CategoriaAvatar, ErrorTienda, ParteAvatar

# Orden y icono de las pestañas. Una categoría solo aparece si hay algo que elegir
# (al menos dos partes); hoy "base" y "cara" tienen una sola, así que no se muestran.
PESTANAS = [
    (CategoriaAvatar.PELO, 'fa-user'),
    (CategoriaAvatar.CAMISA, 'fa-tshirt'),
    (CategoriaAvatar.PANTALON, 'fa-socks'),
    (CategoriaAvatar.CARA, 'fa-smile'),
    (CategoriaAvatar.BASE, 'fa-child'),
]


class TiendaView(LoginRequiredMixin, HeroMixin, TemplateView):
    template_name = 'tienda/tienda.html'
    titulo = 'Tienda de avatares'
    icono = 'fa-store'
    subtitulo = 'Gasta tus puntos en partes nuevas y personaliza tu avatar.'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        puestas = usuario.avatar_equipado()
        compradas = set(usuario.partes_adquiridas.values_list('parte_id', flat=True))

        por_categoria = {}
        for parte in ParteAvatar.objects.order_by('numero'):
            por_categoria.setdefault(parte.categoria, []).append(parte)

        categorias = []
        for categoria, icono in PESTANAS:
            partes = por_categoria.get(categoria.value, [])
            if len(partes) < 2:
                continue
            puesta = puestas.get(categoria.value)
            items = [{
                'parte': p,
                'propia': p.es_gratis or p.pk in compradas,
                'puesta': bool(puesta and puesta.pk == p.pk),
                'falta': max(0, p.precio - usuario.puntos_disponibles),
            } for p in partes]
            categorias.append({
                'clave': categoria.value,
                'nombre': categoria.label,
                'icono': icono,
                'items': items,
                'tienes': sum(1 for i in items if i['propia']),
                'total': len(items),
            })

        claves = [c['clave'] for c in categorias]
        pedida = self.request.GET.get('categoria')
        activa = pedida if pedida in claves else (claves[0] if claves else '')
        contexto.update(
            categorias=categorias,
            activa=activa,
            categoria_activa=next((c for c in categorias if c['clave'] == activa), None),
        )
        return contexto


class _AccionTiendaView(LoginRequiredMixin, View):
    """Comprar y equipar solo se aceptan por POST (con CSRF) y vuelven a la pestaña de la parte."""
    http_method_names = ['post']

    def volver(self, parte):
        return redirect(f"{reverse('tienda:tienda')}?categoria={parte.categoria}")


class ComprarView(_AccionTiendaView):
    def post(self, request, pk):
        parte = get_object_or_404(ParteAvatar, pk=pk)
        try:
            parte = request.user.comprar(parte)
        except ErrorTienda as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'¡Compraste «{parte.nombre}» por {parte.precio} puntos! Ya la llevas puesta.')
        return self.volver(parte)


class EquiparView(_AccionTiendaView):
    def post(self, request, pk):
        parte = get_object_or_404(ParteAvatar, pk=pk)
        try:
            request.user.equipar(parte)
        except ErrorTienda as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'Ahora llevas «{parte.nombre}».')
        return self.volver(parte)
