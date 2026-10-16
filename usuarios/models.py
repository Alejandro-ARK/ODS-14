from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction
from django.db.models import Q
from django.templatetags.static import static
from django.utils import timezone

PUNTOS_POR_NIVEL = 100

# Insignias que se desbloquean al acumular puntos (se muestran en "Mi perfil").
INSIGNIAS = [
    {'umbral': 0,   'nombre': 'Explorador/a novato/a',   'icono': 'fa-seedling'},
    {'umbral': 50,  'nombre': 'Guardián/a del arrecife',  'icono': 'fa-water'},
    {'umbral': 150, 'nombre': 'Defensor/a de los mares',  'icono': 'fa-shield-alt'},
    {'umbral': 300, 'nombre': 'Héroe/heroína del océano', 'icono': 'fa-medal'},
]


class CategoriaAvatar(models.TextChoices):
    """
    Tipos de parte del avatar. El ORDEN de esta lista es el orden de apilado de los
    PNG (el primero va al fondo y el último queda encima). Para cambiar qué capa
    queda sobre cuál, basta con reordenar estas líneas.
    """
    BASE = 'base', 'Base'
    CARA = 'cara', 'Cara'
    PELO = 'pelo', 'Pelo'
    CAMISA = 'camisa', 'Camisa'
    PANTALON = 'pantalon', 'Pantalón'


ORDEN_CAPAS = list(CategoriaAvatar.values)


class ErrorTienda(Exception):
    """Compra o cambio de avatar rechazado. El mensaje se puede mostrar tal cual al usuario."""


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, correo, password, **extra):
        if not correo:
            raise ValueError('El correo electrónico es obligatorio.')
        # El correo se guarda siempre en minúsculas: en MySQL la comparación
        # no distinguía mayúsculas, así que aquí se garantiza el mismo comportamiento.
        usuario = self.model(correo=correo.strip().lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, correo, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._crear(correo, password, **extra)

    def create_superuser(self, correo, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        if extra.get('is_staff') is not True or extra.get('is_superuser') is not True:
            raise ValueError('Un superusuario debe tener is_staff=True e is_superuser=True.')
        return self._crear(correo, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Equivale a la tabla `usuarios` del sitio PHP.

    El correo es el identificador de inicio de sesión; "nombre" es el nombre
    de perfil visible, que el usuario puede cambiar sin afectar su acceso.
    La contraseña vive en el campo `password` (heredado de AbstractBaseUser).
    """
    correo = models.EmailField('correo electrónico', max_length=255, unique=True)
    nombre = models.CharField('nombre de perfil', max_length=60)
    puntos = models.PositiveIntegerField(default=0)
    nivel = models.PositiveIntegerField(default=1)
    fecha_registro = models.DateTimeField('fecha de registro', default=timezone.now)

    # `puntos` es el TOTAL ganado (de él salen el nivel y las insignias, y nunca baja).
    # Lo que se gasta en la tienda se acumula aparte en `puntos_gastados`.
    puntos_gastados = models.PositiveIntegerField('puntos gastados en la tienda', default=0)

    # Partes del avatar que lleva puesto. Vacío (NULL) = la parte gratuita por defecto.
    avatar_base = models.ForeignKey(
        'ParteAvatar', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        limit_choices_to={'categoria': 'base'}, verbose_name='base del avatar')
    avatar_cara = models.ForeignKey(
        'ParteAvatar', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        limit_choices_to={'categoria': 'cara'}, verbose_name='cara del avatar')
    avatar_pelo = models.ForeignKey(
        'ParteAvatar', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        limit_choices_to={'categoria': 'pelo'}, verbose_name='pelo del avatar')
    avatar_camisa = models.ForeignKey(
        'ParteAvatar', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        limit_choices_to={'categoria': 'camisa'}, verbose_name='camisa del avatar')
    avatar_pantalon = models.ForeignKey(
        'ParteAvatar', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        limit_choices_to={'categoria': 'pantalon'}, verbose_name='pantalón del avatar')

    is_active = models.BooleanField('activo', default=True)
    is_staff = models.BooleanField('acceso al panel de administración', default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self):
        return self.correo

    def get_full_name(self):
        return self.nombre

    def get_short_name(self):
        return self.nombre

    # --- Datos derivados que usan las plantillas -------------------------
    @property
    def inicial(self):
        return self.nombre[:1].upper()

    @property
    def porcentaje_nivel(self):
        """Avance (0-99) hacia el siguiente nivel; alimenta la barra de progreso."""
        return self.puntos % PUNTOS_POR_NIVEL

    @property
    def insignias(self):
        return [dict(ins, desbloqueada=self.puntos >= ins['umbral']) for ins in INSIGNIAS]

    @property
    def puntos_disponibles(self):
        """Puntos que aún se pueden gastar en la tienda."""
        return max(0, self.puntos - self.puntos_gastados)

    # --- Avatar ----------------------------------------------------------
    def avatar_equipado(self):
        """
        {categoría: ParteAvatar} con lo que lleva puesto. Hace UNA sola consulta (queda en
        caché en la instancia) y, si una categoría está vacía, usa la parte gratuita de
        menor número.
        """
        cache = getattr(self, '_avatar_cache', None)
        if cache is not None:
            return cache
        ids = [getattr(self, f'avatar_{c}_id') for c in ORDEN_CAPAS]
        partes = list(ParteAvatar.objects.filter(
            Q(pk__in=[i for i in ids if i]) | Q(precio=0)).order_by('numero'))
        por_pk = {p.pk: p for p in partes}
        equipado = {}
        for categoria, pk in zip(ORDEN_CAPAS, ids):
            parte = por_pk.get(pk)
            if parte is None or parte.categoria != categoria:
                parte = next((p for p in partes if p.categoria == categoria and p.precio == 0), None)
            equipado[categoria] = parte
        self._avatar_cache = equipado
        return equipado

    def capas_avatar(self, probando=None):
        """URLs de los PNG a apilar, de abajo hacia arriba. `probando` cambia una parte (vista previa)."""
        equipado = dict(self.avatar_equipado())
        if probando is not None:
            equipado[probando.categoria] = probando
        return [equipado[c].url for c in ORDEN_CAPAS if equipado.get(c)]

    def tiene_parte(self, parte):
        """Las partes gratuitas son de todos; las demás, solo si se compraron."""
        return parte.precio == 0 or self.partes_adquiridas.filter(parte=parte).exists()

    def equipar(self, parte):
        if not self.tiene_parte(parte):
            raise ErrorTienda('Todavía no tienes esa parte: cómprala primero en la tienda.')
        campo = f'avatar_{parte.categoria}'
        setattr(self, campo, parte)
        self.save(update_fields=[campo])
        self._avatar_cache = None

    def comprar(self, parte):
        """
        Compra una parte con los puntos disponibles y la deja puesta. Todo ocurre en una
        transacción con la fila del usuario bloqueada, para que dos compras simultáneas no
        puedan gastar dos veces los mismos puntos.
        """
        with transaction.atomic():
            fila = type(self).objects.select_for_update().get(pk=self.pk)
            parte = ParteAvatar.objects.get(pk=parte.pk)   # precio vigente, no el de la página abierta
            if parte.precio == 0 or ParteAdquirida.objects.filter(usuario=fila, parte=parte).exists():
                raise ErrorTienda(f'Ya tienes «{parte.nombre}».')
            if fila.puntos_disponibles < parte.precio:
                falta = parte.precio - fila.puntos_disponibles
                raise ErrorTienda(f'Te faltan {falta} puntos para comprar «{parte.nombre}».')
            ParteAdquirida.objects.create(usuario=fila, parte=parte, precio_pagado=parte.precio)
            campo = f'avatar_{parte.categoria}'
            fila.puntos_gastados += parte.precio
            setattr(fila, campo, parte)   # se estrena puesta
            fila.save(update_fields=['puntos_gastados', campo])
        self.puntos_gastados = fila.puntos_gastados
        setattr(self, campo, parte)
        self._avatar_cache = None
        return parte

    # --- Lógica de puntos ------------------------------------------------
    @staticmethod
    def calcular_nivel(puntos):
        return puntos // PUNTOS_POR_NIVEL + 1

    def sumar_puntos(self, cantidad):
        """Suma puntos y recalcula el nivel de forma atómica."""
        with transaction.atomic():
            fila = type(self).objects.select_for_update().get(pk=self.pk)
            fila.puntos += cantidad
            fila.nivel = self.calcular_nivel(fila.puntos)
            fila.save(update_fields=['puntos', 'nivel'])
        self.puntos, self.nivel = fila.puntos, fila.nivel


class ParteAvatar(models.Model):
    """
    Catálogo de partes del avatar (una fila por PNG). Precio 0 = gratis y disponible para
    todos los usuarios; cualquier otro precio hay que pagarlo en la tienda.
    Los precios y nombres se pueden editar desde el panel /admin/.
    """
    categoria = models.CharField(max_length=10, choices=CategoriaAvatar.choices)
    numero = models.PositiveSmallIntegerField(help_text='El número que lleva el PNG (Pelo3.png → 3).')
    nombre = models.CharField(max_length=60)
    precio = models.PositiveIntegerField(default=0, help_text='En puntos. 0 = gratis para todos.')
    archivo = models.CharField(
        max_length=150, help_text='Ruta del PNG dentro de la carpeta static/ (p. ej. avatar/Base_Avatar_Pelo1.png).')

    class Meta:
        verbose_name = 'parte de avatar'
        verbose_name_plural = 'partes de avatar'
        ordering = ['categoria', 'numero']
        constraints = [
            models.UniqueConstraint(fields=['categoria', 'numero'], name='parte_avatar_unica_por_categoria_y_numero'),
        ]

    def __str__(self):
        return f'{self.get_categoria_display()} {self.numero} · {self.nombre}'

    @property
    def url(self):
        return static(self.archivo)

    @property
    def es_gratis(self):
        return self.precio == 0


class ParteAdquirida(models.Model):
    """Una parte de pago que un usuario compró (las gratuitas no se registran aquí)."""
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='partes_adquiridas')
    parte = models.ForeignKey(ParteAvatar, on_delete=models.CASCADE, related_name='compras')
    precio_pagado = models.PositiveIntegerField()
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'parte adquirida'
        verbose_name_plural = 'partes adquiridas'
        ordering = ['-fecha']
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'parte'], name='parte_adquirida_unica_por_usuario'),
        ]

    def __str__(self):
        return f'{self.usuario} · {self.parte}'
