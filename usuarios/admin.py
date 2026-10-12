from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UsuarioChangeForm, UsuarioCreationForm
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ('correo', 'nombre', 'puntos', 'nivel', 'fecha_registro', 'is_staff')
    list_filter = ('is_staff', 'is_active', 'nivel')
    search_fields = ('correo', 'nombre')
    ordering = ('-puntos', 'correo')

    fieldsets = (
        (None, {'fields': ('correo', 'password')}),
        ('Perfil y progreso', {'fields': ('nombre', 'puntos', 'nivel', 'fecha_registro')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Actividad', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('correo', 'nombre', 'password1', 'password2')}),
    )
