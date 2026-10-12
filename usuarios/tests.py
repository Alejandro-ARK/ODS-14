import csv
import tempfile
from io import StringIO
from pathlib import Path

import bcrypt
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse

from .management.commands.importar_usuarios import convertir_hash_php
from .models import Usuario


def crear(correo='ana@correo.co', clave='secreto1', **kw):
    kw.setdefault('nombre', 'Ana')
    return Usuario.objects.create_user(correo, clave, **kw)


class RegistroTests(TestCase):
    url = property(lambda s: reverse('usuarios:registro'))

    def datos(self, **kw):
        d = {'nombre': 'Luis', 'correo': 'Luis@Correo.CO', 'contrasena': 'abcdef', 'contrasena2': 'abcdef'}
        d.update(kw)
        return d

    def test_registro_exitoso_inicia_sesion_y_guarda_en_minusculas(self):
        r = self.client.post(self.url, self.datos())
        self.assertRedirects(r, reverse('core:inicio'))
        u = Usuario.objects.get()
        self.assertEqual((u.correo, u.nombre, u.puntos, u.nivel), ('luis@correo.co', 'Luis', 0, 1))
        self.assertTrue(u.check_password('abcdef'))
        self.assertEqual(int(self.client.session['_auth_user_id']), u.pk)

    def test_mensajes_de_error_identicos_al_sitio_php(self):
        casos = [
            ({'nombre': ''}, 'Por favor completa todos los campos.'),
            ({'correo': 'no-es-correo'}, 'Ingresa un correo electrónico válido.'),
            ({'nombre': 'x' * 61}, 'El nombre de perfil es demasiado largo (máximo 60 caracteres).'),
            ({'contrasena2': 'otra'}, 'Las contraseñas no coinciden.'),
            ({'contrasena': '12345', 'contrasena2': '12345'}, 'La contraseña debe tener al menos 6 caracteres.'),
        ]
        for cambio, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                r = self.client.post(self.url, self.datos(**cambio))
                self.assertContains(r, mensaje)
                self.assertEqual(Usuario.objects.count(), 0)

    def test_correo_duplicado_sin_importar_mayusculas(self):
        crear('luis@correo.co')
        r = self.client.post(self.url, self.datos())
        self.assertContains(r, 'Ese correo ya está registrado. Intenta iniciar sesión.')
        self.assertEqual(Usuario.objects.count(), 1)

    def test_el_formulario_conserva_lo_escrito_al_fallar(self):
        r = self.client.post(self.url, self.datos(contrasena2='x'))
        self.assertContains(r, 'value="Luis"')


class LoginLogoutTests(TestCase):
    def test_login_correcto(self):
        crear()
        r = self.client.post(reverse('usuarios:login'), {'correo': ' ANA@correo.co ', 'contrasena': 'secreto1'})
        self.assertRedirects(r, reverse('core:inicio'))

    def test_login_incorrecto(self):
        crear()
        r = self.client.post(reverse('usuarios:login'), {'correo': 'ana@correo.co', 'contrasena': 'mala'})
        self.assertContains(r, 'Correo o contraseña incorrectos.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_usuario_inactivo_no_entra(self):
        crear(is_active=False)
        r = self.client.post(reverse('usuarios:login'), {'correo': 'ana@correo.co', 'contrasena': 'secreto1'})
        self.assertContains(r, 'Correo o contraseña incorrectos.')

    def test_next_se_respeta_solo_si_es_del_mismo_sitio(self):
        crear()
        d = {'correo': 'ana@correo.co', 'contrasena': 'secreto1'}
        r = self.client.post(reverse('usuarios:login') + '?next=/perfil/', d)
        self.assertRedirects(r, '/perfil/')
        self.client.logout()
        r = self.client.post(reverse('usuarios:login') + '?next=https://malo.example/', d)
        self.assertRedirects(r, reverse('core:inicio'))

    def test_logout_solo_por_post(self):
        crear()
        self.client.login(username='ana@correo.co', password='secreto1')
        self.assertEqual(self.client.get(reverse('usuarios:logout')).status_code, 405)
        r = self.client.post(reverse('usuarios:logout'))
        self.assertRedirects(r, reverse('core:inicio'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_con_sesion_login_y_registro_redirigen(self):
        crear()
        self.client.login(username='ana@correo.co', password='secreto1')
        for n in ['login', 'registro']:
            self.assertRedirects(self.client.get(reverse(f'usuarios:{n}')), reverse('core:inicio'))


class PerfilTests(TestCase):
    def test_requiere_sesion(self):
        r = self.client.get(reverse('usuarios:perfil'))
        self.assertRedirects(r, reverse('usuarios:login') + '?next=' + reverse('usuarios:perfil'))

    def test_cambiar_nombre(self):
        u = crear()
        self.client.force_login(u)
        r = self.client.post(reverse('usuarios:perfil'), {'nombre': '  Ana María '}, follow=True)
        self.assertContains(r, '¡Tu nombre de perfil se actualizó correctamente!')
        u.refresh_from_db()
        self.assertEqual(u.nombre, 'Ana María')

    def test_nombre_vacio_o_largo(self):
        u = crear()
        self.client.force_login(u)
        r = self.client.post(reverse('usuarios:perfil'), {'nombre': '   '})
        self.assertContains(r, 'El nombre de perfil no puede estar vacío.')
        r = self.client.post(reverse('usuarios:perfil'), {'nombre': 'x' * 61})
        self.assertContains(r, 'demasiado largo')
        u.refresh_from_db()
        self.assertEqual(u.nombre, 'Ana')

    def test_insignias_segun_puntos(self):
        u = crear(puntos=60)
        self.client.force_login(u)
        html = self.client.get(reverse('usuarios:perfil')).content.decode()
        self.assertEqual(html.count('insignia desbloqueada'), 2)   # 0+ y 50+
        self.assertEqual(html.count('insignia bloqueada'), 2)      # 150+ y 300+


class GuardarPuntosTests(TestCase):
    url = property(lambda s: reverse('usuarios:guardar_puntos'))

    def test_sin_sesion(self):
        r = self.client.post(self.url, {'puntos': 10})
        self.assertEqual(r.status_code, 401)
        self.assertFalse(r.json()['ok'])

    def test_suma_y_recalcula_nivel(self):
        u = crear(puntos=90)
        self.client.force_login(u)
        r = self.client.post(self.url, {'puntos': 20})
        self.assertEqual(r.json(), {'ok': True, 'puntos': 110, 'nivel': 2})
        u.refresh_from_db()
        self.assertEqual((u.puntos, u.nivel), (110, 2))

    def test_tope_de_100_por_actividad(self):
        u = crear()
        self.client.force_login(u)
        self.assertEqual(self.client.post(self.url, {'puntos': 5000}).json()['puntos'], 100)

    def test_valores_invalidos(self):
        u = crear()
        self.client.force_login(u)
        for valor in ['0', '-5', 'abc', '']:
            with self.subTest(valor=valor):
                self.assertEqual(self.client.post(self.url, {'puntos': valor}).status_code, 400)
        u.refresh_from_db()
        self.assertEqual(u.puntos, 0)

    def test_get_no_permitido_y_csrf_exigido(self):
        u = crear()
        self.client.force_login(u)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        estricto = Client(enforce_csrf_checks=True)
        estricto.force_login(u)
        self.assertEqual(estricto.post(self.url, {'puntos': 10}).status_code, 403)


class ImportarUsuariosTests(TestCase):
    CLAVE = 'miClave123'

    def hash_php(self):
        # password_hash() de PHP produce bcrypt con prefijo $2y$
        h = bcrypt.hashpw(self.CLAVE.encode(), bcrypt.gensalt(rounds=4)).decode()
        return '$2y$' + h[4:]

    def escribir_csv(self, filas):
        f = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, newline='', encoding='utf-8-sig')
        w = csv.writer(f)
        w.writerow(['id', 'correo', 'nombre', 'contrasena', 'puntos', 'nivel', 'fecha_registro'])
        w.writerows(filas)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name

    def test_convertir_hash(self):
        h = self.hash_php()
        self.assertEqual(convertir_hash_php(h), 'bcrypt$$2b$' + h[4:])
        self.assertIsNone(convertir_hash_php('texto-plano'))
        self.assertIsNone(convertir_hash_php(''))

    def test_importa_y_el_usuario_entra_con_su_clave_de_siempre(self):
        ruta = self.escribir_csv([
            [1, 'Vieja@Correo.co', 'Vieja', self.hash_php(), 135, 2, '2026-03-04 10:20:30'],
            [2, 'sin-hash@correo.co', 'X', 'plano', 0, 1, ''],
            [3, '', 'Y', self.hash_php(), 0, 1, ''],
        ])
        out = StringIO()
        call_command('importar_usuarios', ruta, stdout=out)
        self.assertIn('1 usuario(s) importado(s), 2 omitido(s)', out.getvalue())

        u = Usuario.objects.get()
        self.assertEqual((u.correo, u.puntos, u.nivel), ('vieja@correo.co', 135, 2))
        self.assertEqual(u.fecha_registro.year, 2026)
        self.assertTrue(self.client.login(username='vieja@correo.co', password=self.CLAVE))
        self.assertFalse(Client().login(username='vieja@correo.co', password='incorrecta'))
        # Tras entrar, Django actualiza el hash al algoritmo preferido
        u.refresh_from_db()
        self.assertTrue(u.password.startswith('pbkdf2_sha256$'))

    def test_no_duplica_si_se_ejecuta_dos_veces(self):
        ruta = self.escribir_csv([[1, 'a@b.co', 'A', self.hash_php(), 0, 1, '']])
        call_command('importar_usuarios', ruta, stdout=StringIO())
        out = StringIO()
        call_command('importar_usuarios', ruta, stdout=out)
        self.assertEqual(Usuario.objects.count(), 1)
        self.assertIn('0 usuario(s) importado(s), 1 omitido(s)', out.getvalue())

    def test_csv_sin_encabezados_da_error_claro(self):
        f = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8')
        f.write('1,a@b.co,A,hash,0,1,\n')
        f.close()
        self.addCleanup(Path(f.name).unlink)
        with self.assertRaisesMessage(CommandError, 'no tiene las columnas'):
            call_command('importar_usuarios', f.name)


class AdminTests(TestCase):
    def test_panel_admin_funciona_con_el_modelo_propio(self):
        Usuario.objects.create_superuser('admin@correo.co', 'admin123', nombre='Admin')
        self.client.login(username='admin@correo.co', password='admin123')
        for url in ['/admin/usuarios/usuario/', '/admin/usuarios/usuario/add/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        r = self.client.post('/admin/usuarios/usuario/add/', {
            'correo': 'nuevo@correo.co', 'nombre': 'Nuevo', 'password1': 'clave-larga-1', 'password2': 'clave-larga-1',
        })
        self.assertEqual(r.status_code, 302)
        nuevo = Usuario.objects.get(correo='nuevo@correo.co')
        self.assertEqual(self.client.get(f'/admin/usuarios/usuario/{nuevo.pk}/change/').status_code, 200)
