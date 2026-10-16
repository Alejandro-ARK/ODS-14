"""Avatar por capas, catálogo de partes, compras con puntos y cuentas nuevas."""
from django.contrib.staticfiles import finders
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from .models import ORDEN_CAPAS, ErrorTienda, ParteAdquirida, ParteAvatar, Usuario


def parte(categoria, numero):
    return ParteAvatar.objects.get(categoria=categoria, numero=numero)


def crear(correo='ana@correo.co', puntos=0, **kw):
    usuario = Usuario.objects.create_user(correo, 'secreto1', nombre=kw.pop('nombre', 'Ana'), **kw)
    if puntos:
        usuario.sumar_puntos(puntos)
    return usuario


class CatalogoTests(TestCase):
    """El catálogo lo carga la migración 0003: debe existir en cualquier base de datos nueva."""

    def test_hay_16_partes_y_5_son_gratis(self):
        self.assertEqual(ParteAvatar.objects.count(), 16)
        gratis = ParteAvatar.objects.filter(precio=0)
        self.assertEqual(sorted(gratis.values_list('categoria', 'numero')),
                         [('base', 0), ('camisa', 0), ('cara', 0), ('pantalon', 0), ('pelo', 0)])
        self.assertEqual(ParteAvatar.objects.filter(precio__gt=0).count(), 11)

    def test_cada_parte_tiene_su_png_en_static(self):
        for p in ParteAvatar.objects.all():
            with self.subTest(parte=str(p)):
                self.assertIsNotNone(finders.find(p.archivo), f'Falta static/{p.archivo}')

    def test_el_orden_de_capas_es_el_enumerado(self):
        self.assertEqual(ORDEN_CAPAS, ['base', 'cara', 'pelo', 'camisa', 'pantalon'])


class UsuarioNuevoTests(TestCase):
    def test_empieza_solo_con_las_partes_gratis(self):
        u = crear()
        self.assertEqual(u.puntos_gastados, 0)
        for categoria, parte_puesta in u.avatar_equipado().items():
            self.assertEqual(parte_puesta.numero, 0, categoria)
        self.assertEqual(u.partes_adquiridas.count(), 0)
        self.assertTrue(all(u.tiene_parte(p) for p in ParteAvatar.objects.filter(precio=0)))
        self.assertFalse(any(u.tiene_parte(p) for p in ParteAvatar.objects.filter(precio__gt=0)))

    def test_capas_en_orden_de_apilado(self):
        capas = crear().capas_avatar()
        self.assertEqual(len(capas), 5)
        nombres = [c.rsplit('/', 1)[-1] for c in capas]
        self.assertEqual(nombres, ['Base_Avatar0.png', 'Base_Avatar_Cara0.png', 'Base_Avatar_Pelo0.png',
                                   'Base_Avatar_Camisa0.png', 'Base_Avatar_Pantalon0.png'])

    def test_no_puede_ponerse_una_parte_que_no_compro(self):
        u = crear(puntos=500)
        with self.assertRaisesMessage(ErrorTienda, 'Todavía no tienes esa parte'):
            u.equipar(parte('pelo', 2))
        u.refresh_from_db()
        self.assertIsNone(u.avatar_pelo_id)

    def test_puede_cambiar_entre_partes_gratis(self):
        u = crear()
        u.equipar(parte('pelo', 0))
        self.assertEqual(u.avatar_pelo, parte('pelo', 0))

    def test_avatar_equipado_hace_una_sola_consulta(self):
        u = crear()
        with self.assertNumQueries(1):
            u.avatar_equipado()
            u.avatar_equipado()
            u.capas_avatar()


class CompraTests(TestCase):
    def test_compra_descuenta_disponibles_pero_no_el_total_ni_el_nivel(self):
        u = crear(puntos=150)                       # nivel 2, tercera insignia desbloqueada
        antes = sum(i['desbloqueada'] for i in u.insignias)
        u.comprar(parte('pelo', 1))                 # 60 pts
        u.refresh_from_db()
        self.assertEqual((u.puntos, u.puntos_gastados, u.puntos_disponibles), (150, 60, 90))
        self.assertEqual(u.nivel, 2)
        self.assertEqual(sum(i['desbloqueada'] for i in u.insignias), antes)
        compra = ParteAdquirida.objects.get()
        self.assertEqual((compra.usuario, compra.parte, compra.precio_pagado), (u, parte('pelo', 1), 60))

    def test_lo_comprado_queda_puesto_y_se_conserva_al_cambiar(self):
        u = crear(puntos=200)
        u.comprar(parte('camisa', 1))
        self.assertEqual(u.avatar_equipado()['camisa'], parte('camisa', 1))
        u.equipar(parte('camisa', 0))               # volver a la gratis
        self.assertEqual(u.avatar_equipado()['camisa'], parte('camisa', 0))
        u.equipar(parte('camisa', 1))               # ya es suya: no se vuelve a pagar
        self.assertEqual(u.puntos_gastados, 40)

    def test_puntos_insuficientes(self):
        u = crear(puntos=40)
        with self.assertRaisesMessage(ErrorTienda, 'Te faltan 20 puntos'):
            u.comprar(parte('pelo', 1))             # cuesta 60
        u.refresh_from_db()
        self.assertEqual((u.puntos_gastados, ParteAdquirida.objects.count()), (0, 0))
        self.assertIsNone(u.avatar_pelo_id)

    def test_no_se_compra_dos_veces_ni_se_compra_lo_gratis(self):
        u = crear(puntos=300)
        u.comprar(parte('pelo', 1))
        with self.assertRaisesMessage(ErrorTienda, 'Ya tienes'):
            u.comprar(parte('pelo', 1))
        with self.assertRaisesMessage(ErrorTienda, 'Ya tienes'):
            u.comprar(parte('pelo', 0))
        u.refresh_from_db()
        self.assertEqual(u.puntos_gastados, 60)

    def test_dos_pestanas_con_datos_viejos_no_gastan_dos_veces_los_mismos_puntos(self):
        """Simula dos peticiones simultáneas: la segunda lee su saldo desactualizado."""
        u = crear(puntos=100)
        pestana_a, pestana_b = Usuario.objects.get(pk=u.pk), Usuario.objects.get(pk=u.pk)
        pestana_a.comprar(parte('pelo', 1))         # 60 → quedan 40
        with self.assertRaisesMessage(ErrorTienda, 'Te faltan 20 puntos'):
            pestana_b.comprar(parte('camisa', 3))   # 60, pero en la BD ya solo hay 40
        u.refresh_from_db()
        self.assertEqual(u.puntos_gastados, 60)

    def test_se_paga_el_precio_vigente_y_no_el_de_la_pagina_abierta(self):
        u = crear(puntos=60)
        pagina_vieja = parte('pelo', 1)             # el usuario vio 60 puntos…
        ParteAvatar.objects.filter(pk=pagina_vieja.pk).update(precio=90)   # …y luego el admin lo subió
        with self.assertRaisesMessage(ErrorTienda, 'Te faltan 30 puntos'):
            u.comprar(pagina_vieja)

    def test_ganar_puntos_despues_de_gastar(self):
        u = crear(puntos=100)
        u.comprar(parte('camisa', 1))               # 40
        u.sumar_puntos(50)
        u.refresh_from_db()
        self.assertEqual((u.puntos, u.puntos_gastados, u.puntos_disponibles, u.nivel), (150, 40, 110, 2))

    def test_si_un_admin_baja_los_puntos_el_saldo_no_queda_negativo(self):
        u = crear(puntos=100)
        u.comprar(parte('camisa', 1))
        Usuario.objects.filter(pk=u.pk).update(puntos=10)
        u.refresh_from_db()
        self.assertEqual(u.puntos_disponibles, 0)


class IntegridadTests(TestCase):
    def test_borrar_un_usuario_borra_sus_compras(self):
        u = crear(puntos=100)
        u.comprar(parte('pelo', 1))
        u.delete()
        self.assertEqual(ParteAdquirida.objects.count(), 0)
        self.assertEqual(ParteAvatar.objects.count(), 16)

    def test_si_se_borra_una_parte_el_avatar_vuelve_al_valor_por_defecto(self):
        u = crear(puntos=100)
        u.comprar(parte('pelo', 1))
        parte('pelo', 1).delete()
        u = Usuario.objects.get(pk=u.pk)
        self.assertEqual(u.avatar_equipado()['pelo'], parte('pelo', 0))

    def test_una_parte_en_la_categoria_equivocada_se_ignora(self):
        u = crear()
        Usuario.objects.filter(pk=u.pk).update(avatar_pelo=parte('camisa', 2))   # dato corrupto
        u = Usuario.objects.get(pk=u.pk)
        self.assertEqual(u.avatar_equipado()['pelo'], parte('pelo', 0))

    def test_no_se_repite_la_misma_categoria_y_numero(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            ParteAvatar.objects.create(categoria='pelo', numero=1, nombre='Duplicada', archivo='x.png')


class EtiquetaAvatarTests(TestCase):
    def test_dibuja_las_cinco_capas_con_texto_alternativo(self):
        u = crear(nombre='Luisa')
        html = Template('{% load avatar %}{% avatar u 40 %}').render(Context({'u': u}))
        self.assertEqual(html.count('<img'), 5)
        self.assertIn('role="img"', html)
        self.assertIn('aria-label="Avatar de Luisa"', html)
        self.assertIn('--tam: 40px', html)
        self.assertIn('mo-avatar-busto', html)

    def test_modo_completo_y_vista_previa(self):
        u = crear()
        html = Template("{% load avatar %}{% avatar_probando u p 160 'completo' %}").render(
            Context({'u': u, 'p': parte('pelo', 3)}))
        self.assertIn('mo-avatar-completo', html)
        self.assertIn('Base_Avatar_Pelo3.png', html)
        self.assertNotIn('Base_Avatar_Pelo0.png', html)
        # La vista previa no cambia lo que el usuario lleva puesto de verdad
        self.assertEqual(u.avatar_equipado()['pelo'], parte('pelo', 0))


class AdminAvatarTests(TestCase):
    def setUp(self):
        Usuario.objects.create_superuser('admin@correo.co', 'admin123', nombre='Admin')
        self.client.login(username='admin@correo.co', password='admin123')

    def test_el_catalogo_se_edita_desde_el_admin(self):
        r = self.client.get('/admin/usuarios/parteavatar/')
        self.assertContains(r, 'Media melena con broche')
        p = parte('pelo', 1)
        r = self.client.get(f'/admin/usuarios/parteavatar/{p.pk}/change/')
        self.assertEqual(r.status_code, 200)
        r = self.client.post(f'/admin/usuarios/parteavatar/{p.pk}/change/', {
            'categoria': 'pelo', 'numero': 1, 'nombre': 'Melena', 'precio': 75, 'archivo': p.archivo})
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual((p.nombre, p.precio), ('Melena', 75))

    def test_ficha_de_usuario_con_avatar_y_compras(self):
        u = crear(puntos=100)
        u.comprar(parte('pelo', 1))
        self.assertEqual(self.client.get(f'/admin/usuarios/usuario/{u.pk}/change/').status_code, 200)
        self.assertEqual(self.client.get('/admin/usuarios/parteadquirida/').status_code, 200)
