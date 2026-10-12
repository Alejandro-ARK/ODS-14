from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone

PUNTOS_POR_NIVEL = 100

# Insignias que se desbloquean al acumular puntos (se muestran en "Mi perfil").
INSIGNIAS = [
    {'umbral': 0,   'nombre': 'Explorador/a novato/a',   'icono': 'fa-seedling'},
    {'umbral': 50,  'nombre': 'Guardián/a del arrecife',  'icono': 'fa-water'},
    {'umbral': 150, 'nombre': 'Defensor/a de los mares',  'icono': 'fa-shield-alt'},
    {'umbral': 300, 'nombre': 'Héroe/heroína del océano', 'icono': 'fa-medal'},
]


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
