from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

CLAVE = 'secreto1'


def usuario(correo='ana@correo.co', **kw):
    kw.setdefault('nombre', 'Ana')
    return Usuario.objects.create_user(correo, CLAVE, **kw)


def superusuario(correo='root@correo.co', **kw):
    kw.setdefault('nombre', 'Root')
    return Usuario.objects.create_superuser(correo, CLAVE, **kw)


class AccesoTests(TestCase):
    URLS = [
        reverse('panel:resumen'), reverse('panel:usuarios'), reverse('panel:usuario_crear'),
        reverse('panel:base_datos'), reverse('panel:tabla', args=['usuarios', 'usuario']),
    ]

    def test_anonimo_va_al_login(self):
        for url in self.URLS:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertRedirects(r, f"{reverse('usuarios:login')}?next={url}")

    def test_usuario_normal_recibe_404(self):
        self.client.force_login(usuario())
        for url in self.URLS:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_staff_sin_ser_superusuario_tampoco_entra(self):
        self.client.force_login(usuario(is_staff=True))
        self.assertEqual(self.client.get(reverse('panel:resumen')).status_code, 404)

    def test_superusuario_entra_a_todo(self):
        self.client.force_login(superusuario())
        for url in self.URLS:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_acciones_post_cerradas_a_usuarios_normales(self):
        victima = usuario('victima@correo.co')
        self.client.force_login(usuario())
        for nombre in ['usuario_suspender', 'usuario_reactivar', 'usuario_eliminar']:
            r = self.client.post(reverse(f'panel:{nombre}', args=[victima.pk]))
            self.assertEqual(r.status_code, 404)
        victima.refresh_from_db()
        self.assertTrue(victima.is_active)

    def test_enlace_del_menu_solo_para_superusuarios(self):
        self.client.force_login(usuario())
        self.assertNotContains(self.client.get(reverse('core:inicio')), reverse('panel:resumen'))
        self.client.force_login(superusuario())
        self.assertContains(self.client.get(reverse('core:inicio')), reverse('panel:resumen'))


class CrearUsuarioTests(TestCase):
    url = reverse('panel:usuario_crear')

    def setUp(self):
        self.admin = superusuario()
        self.client.force_login(self.admin)

    def datos(self, **kw):
        d = {'nombre': 'Luis', 'correo': 'Luis@Correo.CO', 'password1': 'abcdef',
             'password2': 'abcdef', 'rol': 'usuario'}
        d.update(kw)
        return d

    def test_crea_usuario_normal(self):
        r = self.client.post(self.url, self.datos())
        self.assertRedirects(r, reverse('panel:usuarios'))
        u = Usuario.objects.get(correo='luis@correo.co')
        self.assertFalse(u.is_superuser or u.is_staff)
        self.assertTrue(u.is_active and u.check_password('abcdef'))

    def test_nuevo_usuario_puede_iniciar_sesion(self):
        self.client.post(self.url, self.datos())
        self.client.logout()
        r = self.client.post(reverse('usuarios:login'), {'correo': 'luis@correo.co', 'contrasena': 'abcdef'})
        self.assertRedirects(r, reverse('core:inicio'))

    def test_crear_superusuario_exige_la_clave_de_quien_lo_crea(self):
        r = self.client.post(self.url, self.datos(rol='superusuario', password_admin='mala'))
        self.assertContains(r, 'Tu contraseña no es correcta.')
        self.assertFalse(Usuario.objects.filter(correo='luis@correo.co').exists())

        r = self.client.post(self.url, self.datos(rol='superusuario', password_admin=CLAVE))
        self.assertRedirects(r, reverse('panel:usuarios'))
        u = Usuario.objects.get(correo='luis@correo.co')
        self.assertTrue(u.is_superuser and u.is_staff)

    def test_errores_de_validacion(self):
        usuario('luis@correo.co')
        casos = [
            ({}, 'Ese correo ya está registrado.'),
            ({'correo': 'otro@correo.co', 'password2': 'distinta'}, 'Las contraseñas no coinciden.'),
            ({'correo': 'otro@correo.co', 'password1': '123', 'password2': '123'}, 'por lo menos 6 caracteres'),
            ({'correo': 'no-es-correo'}, 'Ingresa un correo electrónico válido.'),
            ({'correo': 'otro@correo.co', 'nombre': '   '}, 'obligatorio'),
        ]
        total = Usuario.objects.count()
        for cambio, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                self.assertContains(self.client.post(self.url, self.datos(**cambio)), mensaje)
                self.assertEqual(Usuario.objects.count(), total)


class SuspenderTests(TestCase):
    def setUp(self):
        self.admin = superusuario()
        self.client.force_login(self.admin)

    def test_suspender_y_reactivar(self):
        u = usuario()
        self.client.post(reverse('panel:usuario_suspender', args=[u.pk]))
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.client.post(reverse('panel:usuario_reactivar', args=[u.pk]))
        u.refresh_from_db()
        self.assertTrue(u.is_active)

    def test_suspender_cierra_la_sesion_abierta_del_usuario(self):
        u = usuario()
        otro = self.client_class()
        otro.force_login(u)
        self.assertEqual(otro.get(reverse('usuarios:perfil')).status_code, 200)

        self.client.post(reverse('panel:usuario_suspender', args=[u.pk]))
        self.assertEqual(otro.get(reverse('usuarios:perfil')).status_code, 302)  # ya no está autenticado

    def test_suspendido_no_puede_iniciar_sesion(self):
        u = usuario()
        self.client.post(reverse('panel:usuario_suspender', args=[u.pk]))
        self.client.logout()
        r = self.client.post(reverse('usuarios:login'), {'correo': u.correo, 'contrasena': CLAVE})
        self.assertContains(r, 'Tu cuenta está suspendida.')

    def test_no_puedes_suspenderte_a_ti_mismo(self):
        r = self.client.post(reverse('panel:usuario_suspender', args=[self.admin.pk]), follow=True)
        self.assertContains(r, 'No puedes suspender tu propia cuenta.')
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_puede_suspender_a_otro_superusuario(self):
        otro = superusuario('otro@correo.co')
        self.client.post(reverse('panel:usuario_suspender', args=[otro.pk]))
        otro.refresh_from_db()
        self.assertFalse(otro.is_active)

    def test_suspender_solo_acepta_post(self):
        u = usuario()
        self.assertEqual(self.client.get(reverse('panel:usuario_suspender', args=[u.pk])).status_code, 405)


class EliminarTests(TestCase):
    def setUp(self):
        self.admin = superusuario()
        self.client.force_login(self.admin)

    def test_get_muestra_confirmacion_y_no_borra(self):
        u = usuario()
        r = self.client.get(reverse('panel:usuario_eliminar', args=[u.pk]))
        self.assertContains(r, '¿Eliminar esta cuenta?')
        self.assertTrue(Usuario.objects.filter(pk=u.pk).exists())

    def test_elimina_usuario_normal(self):
        u = usuario()
        r = self.client.post(reverse('panel:usuario_eliminar', args=[u.pk]))
        self.assertRedirects(r, reverse('panel:usuarios'))
        self.assertFalse(Usuario.objects.filter(pk=u.pk).exists())

    def test_eliminar_superusuario_exige_la_clave_de_quien_lo_hace(self):
        otro = superusuario('otro@correo.co')
        url = reverse('panel:usuario_eliminar', args=[otro.pk])

        r = self.client.post(url, {'password_admin': 'mala'})
        self.assertContains(r, 'Tu contraseña no es correcta.')
        self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())

        r = self.client.post(url)   # sin contraseña
        self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())

        r = self.client.post(url, {'password_admin': CLAVE})
        self.assertRedirects(r, reverse('panel:usuarios'))
        self.assertFalse(Usuario.objects.filter(pk=otro.pk).exists())

    def test_no_puedes_eliminarte_a_ti_mismo(self):
        url = reverse('panel:usuario_eliminar', args=[self.admin.pk])
        for metodo in (self.client.get, self.client.post):
            r = metodo(url, {'password_admin': CLAVE}, follow=True)
            self.assertContains(r, 'No puedes eliminar tu propia cuenta.')
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_usuario_inexistente_da_404(self):
        self.assertEqual(self.client.post(reverse('panel:usuario_eliminar', args=[9999])).status_code, 404)

    def test_la_transaccion_se_deshace_si_no_quedaria_ningun_superusuario(self):
        # Red de seguridad ante dos superusuarios que se eliminan a la vez: si tras la acción
        # no quedara ninguno activo, todo se revierte.
        otro = superusuario('otro@correo.co')
        with patch('panel.views._hay_superusuario_activo', return_value=False):
            r = self.client.post(reverse('panel:usuario_eliminar', args=[otro.pk]),
                                 {'password_admin': CLAVE}, follow=True)
            self.assertContains(r, 'debe quedar al menos un superusuario activo')
            self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())

            r = self.client.post(reverse('panel:usuario_suspender', args=[otro.pk]), follow=True)
            self.assertContains(r, 'debe quedar al menos un superusuario activo')
            otro.refresh_from_db()
            self.assertTrue(otro.is_active)


class ListadoTests(TestCase):
    def setUp(self):
        superusuario()
        usuario('ana@correo.co', nombre='Ana')
        usuario('beto@correo.co', nombre='Beto', is_active=False)
        self.client.force_login(Usuario.objects.get(correo='root@correo.co'))

    def get(self, **params):
        return self.client.get(reverse('panel:usuarios'), params)

    def test_busqueda_y_filtros(self):
        self.assertEqual(self.get().context['pagina'].paginator.count, 3)
        self.assertEqual(self.get(q='beto').context['pagina'].paginator.count, 1)
        self.assertEqual(self.get(estado='suspendidos').context['pagina'].paginator.count, 1)
        self.assertEqual(self.get(estado='activos').context['pagina'].paginator.count, 2)
        self.assertEqual(self.get(rol='superusuarios').context['pagina'].paginator.count, 1)
        self.assertEqual(self.get(rol='normales').context['pagina'].paginator.count, 2)

    def test_no_se_ofrecen_acciones_sobre_uno_mismo(self):
        yo = Usuario.objects.get(correo='root@correo.co')
        self.assertNotContains(self.get(), reverse('panel:usuario_eliminar', args=[yo.pk]))


class BaseDatosTests(TestCase):
    def setUp(self):
        self.client.force_login(superusuario())

    def test_lista_las_tablas_con_su_conteo(self):
        r = self.client.get(reverse('panel:base_datos'))
        self.assertContains(r, 'usuarios_usuario')
        self.assertContains(r, 'django_session')

    def test_nunca_muestra_hashes_de_contrasena(self):
        hash_ = Usuario.objects.get().password
        r = self.client.get(reverse('panel:tabla', args=['usuarios', 'usuario']))
        self.assertContains(r, 'root@correo.co')
        self.assertNotContains(r, hash_)

    def test_nunca_muestra_claves_de_sesion(self):
        from django.contrib.sessions.models import Session
        sesion = Session.objects.get()
        r = self.client.get(reverse('panel:tabla', args=['sessions', 'session']))
        self.assertNotContains(r, sesion.session_key)
        self.assertNotContains(r, sesion.session_data)

    def test_tabla_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse('panel:tabla', args=['x', 'y'])).status_code, 404)

    def test_es_de_solo_lectura(self):
        r = self.client.post(reverse('panel:tabla', args=['usuarios', 'usuario']))
        self.assertEqual(r.status_code, 405)
