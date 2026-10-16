from django.test import Client, TestCase
from django.urls import reverse

from usuarios.models import ParteAdquirida, ParteAvatar, Usuario


def parte(categoria, numero):
    return ParteAvatar.objects.get(categoria=categoria, numero=numero)


def usuario_con(puntos=0, correo='ana@correo.co'):
    u = Usuario.objects.create_user(correo, 'secreto1', nombre='Ana')
    if puntos:
        u.sumar_puntos(puntos)
    return u


class AccesoTests(TestCase):
    def test_exige_sesion(self):
        r = self.client.get(reverse('tienda:tienda'))
        self.assertRedirects(r, reverse('usuarios:login') + '?next=' + reverse('tienda:tienda'))

    def test_comprar_y_equipar_sin_sesion_no_hacen_nada(self):
        u = usuario_con(500)
        for nombre in ('comprar', 'equipar'):
            r = self.client.post(reverse(f'tienda:{nombre}', args=[parte('pelo', 1).pk]))
            self.assertEqual(r.status_code, 302)
            self.assertIn('/login/', r['Location'])
        u.refresh_from_db()
        self.assertEqual(ParteAdquirida.objects.count(), 0)

    def test_comprar_y_equipar_no_aceptan_get(self):
        self.client.force_login(usuario_con(500))
        for nombre in ('comprar', 'equipar'):
            self.assertEqual(self.client.get(reverse(f'tienda:{nombre}', args=[parte('pelo', 1).pk])).status_code, 405)

    def test_comprar_exige_csrf(self):
        u = usuario_con(500)
        estricto = Client(enforce_csrf_checks=True)
        estricto.force_login(u)
        r = estricto.post(reverse('tienda:comprar', args=[parte('pelo', 1).pk]))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(ParteAdquirida.objects.count(), 0)

    def test_parte_inexistente_da_404(self):
        self.client.force_login(usuario_con(500))
        self.assertEqual(self.client.post(reverse('tienda:comprar', args=[99999])).status_code, 404)
        self.assertEqual(self.client.post(reverse('tienda:equipar', args=[99999])).status_code, 404)


class PaginaTiendaTests(TestCase):
    def test_muestra_solo_categorias_con_algo_que_elegir(self):
        self.client.force_login(usuario_con())
        r = self.client.get(reverse('tienda:tienda'))
        self.assertEqual([c['nombre'] for c in r.context['categorias']], ['Pelo', 'Camisa', 'Pantalón'])
        self.assertEqual(r.context['activa'], 'pelo')

    def test_pestana_pedida_y_pestana_invalida(self):
        self.client.force_login(usuario_con())
        r = self.client.get(reverse('tienda:tienda') + '?categoria=camisa')
        self.assertEqual(r.context['activa'], 'camisa')
        self.assertContains(r, 'Camiseta roja')
        r = self.client.get(reverse('tienda:tienda') + '?categoria=hacker')
        self.assertEqual(r.context['activa'], 'pelo')

    def test_estados_de_cada_parte(self):
        u = usuario_con(70)                                   # alcanza para 60 pero no para 80
        self.client.force_login(u)
        r = self.client.get(reverse('tienda:tienda') + '?categoria=pelo')
        estado = {i['parte'].numero: i for i in r.context['categoria_activa']['items']}
        self.assertTrue(estado[0]['puesta'] and estado[0]['propia'])      # la gratis, puesta
        self.assertFalse(estado[1]['propia'])
        self.assertEqual(estado[1]['falta'], 0)                           # 60 ≤ 70: se puede comprar
        self.assertEqual(estado[3]['falta'], 10)                          # 80 − 70
        self.assertContains(r, 'La llevas puesta')
        self.assertContains(r, 'Comprar · 60')
        self.assertContains(r, 'Te faltan 10 puntos')
        self.assertContains(r, reverse('tienda:comprar', args=[parte('pelo', 1).pk]))
        self.assertNotContains(r, reverse('tienda:comprar', args=[parte('pelo', 3).pk]))   # bloqueado: sin formulario

    def test_contador_de_partes_por_pestana(self):
        u = usuario_con(500)
        u.comprar(parte('pelo', 1))
        self.client.force_login(u)
        r = self.client.get(reverse('tienda:tienda'))
        pelo = r.context['categorias'][0]
        self.assertEqual((pelo['tienes'], pelo['total']), (2, 6))

    def test_vista_previa_de_cada_parte_lleva_puesta_esa_parte(self):
        self.client.force_login(usuario_con())
        html = self.client.get(reverse('tienda:tienda') + '?categoria=pelo').content.decode()
        for n in range(6):
            self.assertIn(f'Base_Avatar_Pelo{n}.png', html)

    def test_las_consultas_no_crecen_con_el_tamano_del_catalogo(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.force_login(usuario_con(100))

        def consultas():
            with CaptureQueriesContext(connection) as c:
                self.client.get(reverse('tienda:tienda') + '?categoria=pelo')
            return len(c)

        antes = consultas()
        for n in range(10, 40):                                # 30 peinados más en el catálogo
            ParteAvatar.objects.create(categoria='pelo', numero=n, nombre=f'Extra {n}', precio=50,
                                       archivo='avatar/Base_Avatar_Pelo1.png')
        self.assertEqual(consultas(), antes)


class FlujoCompraTests(TestCase):
    def setUp(self):
        self.u = usuario_con(150)
        self.client.force_login(self.u)

    def test_comprar_descuenta_pone_la_parte_y_vuelve_a_la_pestana(self):
        p = parte('pelo', 2)                                   # 100 pts
        r = self.client.post(reverse('tienda:comprar', args=[p.pk]), follow=True)
        self.assertRedirects(r, reverse('tienda:tienda') + '?categoria=pelo')
        self.assertContains(r, '¡Compraste «Voluminoso» por 100 puntos!')
        self.u.refresh_from_db()
        self.assertEqual((self.u.puntos, self.u.puntos_gastados, self.u.puntos_disponibles), (150, 100, 50))
        self.assertEqual(self.u.nivel, 2)
        self.assertEqual(self.u.avatar_pelo, p)
        # El saldo de la barra y del lateral se actualizó
        self.assertContains(r, '<span class="js-puntos-usuario">50</span>', html=True)

    def test_sin_puntos_suficientes_no_cambia_nada(self):
        self.client.post(reverse('tienda:comprar', args=[parte('pelo', 4).pk]))     # 120 de 150 → quedan 30
        r = self.client.post(reverse('tienda:comprar', args=[parte('pelo', 2).pk]), follow=True)   # cuesta 100
        self.assertContains(r, 'Te faltan 70 puntos para comprar «Voluminoso»')
        self.u.refresh_from_db()
        self.assertEqual(self.u.puntos_gastados, 120)                  # solo se cobró la primera
        self.assertEqual(self.u.avatar_pelo, parte('pelo', 4))         # y sigue puesta la primera
        self.assertEqual(ParteAdquirida.objects.count(), 1)

    def test_doble_envio_solo_cobra_una_vez(self):
        url = reverse('tienda:comprar', args=[parte('camisa', 1).pk])
        self.client.post(url)
        r = self.client.post(url, follow=True)
        self.assertContains(r, 'Ya tienes «Camiseta azul»')
        self.u.refresh_from_db()
        self.assertEqual(self.u.puntos_gastados, 40)

    def test_equipar_una_parte_comprada_y_rechazar_una_ajena(self):
        self.u.comprar(parte('camisa', 1))
        self.u.comprar(parte('camisa', 2))                     # ahora lleva la roja
        r = self.client.post(reverse('tienda:equipar', args=[parte('camisa', 1).pk]), follow=True)
        self.assertContains(r, 'Ahora llevas «Camiseta azul»')
        self.u.refresh_from_db()
        self.assertEqual(self.u.avatar_camisa, parte('camisa', 1))

        r = self.client.post(reverse('tienda:equipar', args=[parte('camisa', 3).pk]), follow=True)
        self.assertContains(r, 'Todavía no tienes esa parte')
        self.u.refresh_from_db()
        self.assertEqual(self.u.avatar_camisa, parte('camisa', 1))

    def test_un_usuario_no_afecta_el_avatar_ni_los_puntos_de_otro(self):
        otra = usuario_con(500, correo='otra@correo.co')
        self.client.post(reverse('tienda:comprar', args=[parte('pelo', 1).pk]))
        otra.refresh_from_db()
        self.assertEqual((otra.puntos_gastados, otra.avatar_pelo_id), (0, None))


class AvatarEnElSitioTests(TestCase):
    """La 'imagen de perfil' (círculo con la inicial) fue reemplazada por el avatar."""

    def test_barra_de_navegacion_muestra_el_avatar_y_el_saldo(self):
        u = usuario_con(130)
        u.comprar(parte('pelo', 1))                             # gasta 60 → quedan 70
        self.client.force_login(u)
        html = self.client.get(reverse('core:inicio')).content.decode()
        self.assertIn('mo-avatar-busto', html)
        self.assertIn('Base_Avatar_Pelo1.png', html)
        self.assertNotIn('class="mo-avatar"', html)             # ya no hay círculo con la inicial
        self.assertIn('<span class="js-puntos-usuario">70</span>', html)
        self.assertIn('Puntos disponibles: <strong class="js-puntos-usuario">70</strong>', html)

    def test_perfil_muestra_avatar_completo_y_enlace_a_la_tienda(self):
        u = usuario_con(130)
        self.client.force_login(u)
        r = self.client.get(reverse('usuarios:perfil'))
        self.assertContains(r, 'mo-avatar-completo')
        self.assertContains(r, 'Personalizar mi avatar')
        self.assertContains(r, '130 pts ganados en total')
        self.assertNotContains(r, 'class="mo-avatar mx-auto')

    def test_insignias_no_se_pierden_por_gastar(self):
        u = usuario_con(150)
        u.comprar(parte('pelo', 4))                             # 120
        self.client.force_login(u)
        html = self.client.get(reverse('usuarios:perfil')).content.decode()
        self.assertEqual(html.count('insignia desbloqueada'), 3)   # 0+, 50+ y 150+

    def test_guardar_puntos_devuelve_los_disponibles(self):
        u = usuario_con(100)
        u.comprar(parte('camisa', 1))                           # 40
        self.client.force_login(u)
        r = self.client.post(reverse('usuarios:guardar_puntos'), {'puntos': 50})
        self.assertEqual(r.json(), {'ok': True, 'puntos': 150, 'disponibles': 110, 'nivel': 2})

    def test_enlace_a_la_tienda_en_el_menu_y_pestana_activa(self):
        r = self.client.get(reverse('core:inicio'))              # visitante
        self.assertContains(r, f'href="{reverse("tienda:tienda")}"')
        u = usuario_con()
        self.client.force_login(u)
        r = self.client.get(reverse('tienda:tienda'))
        self.assertContains(r, f'class="nav-link activa" href="{reverse("tienda:tienda")}"')
        self.assertNotContains(r, f'class="nav-link activa" href="{reverse("core:inicio")}"')

    def test_registro_nuevo_usa_las_partes_por_defecto(self):
        self.client.post(reverse('usuarios:registro'), {
            'nombre': 'Luis', 'correo': 'luis@correo.co', 'contrasena': 'abcdef', 'contrasena2': 'abcdef'})
        u = Usuario.objects.get(correo='luis@correo.co')
        self.assertEqual(u.capas_avatar(), [parte(c, 0).url for c in ['base', 'cara', 'pelo', 'camisa', 'pantalon']])
        self.assertEqual(u.puntos_disponibles, 0)


class IntegracionConElPanelTests(TestCase):
    """El panel de superusuarios (app `panel`) no se modificó: debe seguir funcionando con las tablas nuevas."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin@correo.co', 'admin123', nombre='Admin')
        self.client.force_login(self.admin)

    def test_el_explorador_de_base_de_datos_muestra_las_tablas_nuevas(self):
        r = self.client.get(reverse('panel:base_datos'))
        nombres = {t['tabla']: t['filas'] for t in r.context['tablas']}
        self.assertEqual(nombres['usuarios_parteavatar'], 16)
        self.assertIn('usuarios_parteadquirida', nombres)

    def test_se_puede_ver_el_catalogo_y_las_columnas_nuevas_de_usuario(self):
        r = self.client.get(reverse('panel:tabla', args=['usuarios', 'parteavatar']))
        self.assertContains(r, 'Voluminoso')
        r = self.client.get(reverse('panel:tabla', args=['usuarios', 'usuario']))
        for columna in ('puntos_gastados', 'avatar_pelo_id', 'avatar_camisa_id'):
            self.assertContains(r, columna)

    def test_eliminar_una_cuenta_desde_el_panel_borra_sus_compras_pero_no_el_catalogo(self):
        u = usuario_con(200)
        u.comprar(parte('pelo', 1))
        u.comprar(parte('camisa', 1))
        self.assertEqual(ParteAdquirida.objects.count(), 2)
        r = self.client.post(reverse('panel:usuario_eliminar', args=[u.pk]))
        self.assertRedirects(r, reverse('panel:usuarios'))
        self.assertFalse(Usuario.objects.filter(pk=u.pk).exists())
        self.assertEqual(ParteAdquirida.objects.count(), 0)
        self.assertEqual(ParteAvatar.objects.count(), 16)

    def test_las_cuentas_creadas_desde_el_panel_tambien_tienen_avatar_por_defecto(self):
        self.client.post(reverse('panel:usuario_crear'), {
            'nombre': 'Creada', 'correo': 'creada@correo.co',
            'password1': 'clave-larga-1', 'password2': 'clave-larga-1', 'rol': 'usuario'})
        nueva = Usuario.objects.get(correo='creada@correo.co')
        self.assertEqual(len(nueva.capas_avatar()), 5)
