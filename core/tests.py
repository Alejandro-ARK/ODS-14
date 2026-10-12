from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario


class PaginasTests(TestCase):
    def test_todas_las_paginas_responden(self):
        for nombre in ['inicio', 'aprende', 'juega', 'quiz', 'mares', 'actua']:
            with self.subTest(pagina=nombre):
                r = self.client.get(reverse(f'core:{nombre}'))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, 'Misión Océano')

    def test_titulos_y_hero(self):
        r = self.client.get(reverse('core:aprende'))
        self.assertContains(r, '<h1>Aprende</h1>', html=True)
        self.assertContains(r, 'Todo lo que necesitas saber sobre el ODS 14')
        self.assertContains(r, 'mo-hero-chico')
        self.assertContains(self.client.get(reverse('core:inicio')), 'mo-hero-grande')

    def test_navegacion_marca_pagina_activa(self):
        r = self.client.get(reverse('core:mares'))
        self.assertContains(r, f'class="nav-link activa" href="{reverse("core:mares")}"')
        self.assertNotContains(r, f'class="nav-link activa" href="{reverse("core:juega")}"')

    def test_visitante_ve_login_y_registro(self):
        r = self.client.get(reverse('core:inicio'))
        self.assertContains(r, reverse('usuarios:login'))
        self.assertContains(r, 'Registrarme')
        self.assertNotContains(r, 'data-url-guardar-puntos')

    def test_usuario_ve_puntos_y_endpoint(self):
        u = Usuario.objects.create_user('a@b.co', 'secreto1', nombre='Ana', puntos=130, nivel=2)
        self.client.force_login(u)
        r = self.client.get(reverse('core:inicio'))
        self.assertContains(r, 'data-url-guardar-puntos')
        self.assertContains(r, '<span class="js-puntos-usuario">130</span>', html=True)
        self.assertContains(r, 'style="width: 30%"')           # 130 % 100
        self.assertContains(r, 'name="csrf-token"')

    def test_quiz_tiene_contenedor_de_resumen_separado_del_boton(self):
        u = Usuario.objects.create_user('a@b.co', 'secreto1', nombre='Ana')
        self.client.force_login(u)
        r = self.client.get(reverse('core:quiz'))
        self.assertContains(r, 'id="quiz-resumen"')
        self.assertContains(r, 'id="quiz-guardar-puntos"')
        self.assertEqual(r.content.decode().count('data-correcta="1"'), 5)
