from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .forms import UsuarioChangeForm, UsuarioCreationForm
from .models import ParteAdquirida, ParteAvatar, Usuario


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
        ('Perfil y progreso', {'fields': ('nombre', 'puntos', 'puntos_gastados', 'nivel', 'fecha_registro')}),
        ('Avatar', {'fields': ('avatar_base', 'avatar_cara', 'avatar_pelo', 'avatar_camisa', 'avatar_pantalon')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Actividad', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('correo', 'nombre', 'password1', 'password2')}),
    )


@admin.register(ParteAvatar)
class ParteAvatarAdmin(admin.ModelAdmin):
    """Catálogo de la tienda: aquí se cambian precios y nombres (precio 0 = gratis para todos)."""
    list_display = ('miniatura', 'categoria', 'numero', 'nombre', 'precio')
    list_display_links = ('miniatura', 'categoria')
    list_editable = ('nombre', 'precio')
    list_filter = ('categoria',)
    search_fields = ('nombre',)
    ordering = ('categoria', 'numero')

    @admin.display(description='Vista previa')
    def miniatura(self, parte):
        return format_html(
            '<img src="{}" width="56" height="56" '
            'style="image-rendering:pixelated;background:#dfe9f0;border-radius:6px">', parte.url)


@admin.register(ParteAdquirida)
class ParteAdquiridaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'parte', 'precio_pagado', 'fecha')
    list_filter = ('parte__categoria',)
    search_fields = ('usuario__correo', 'usuario__nombre', 'parte__nombre')
    raw_id_fields = ('usuario', 'parte')
    ordering = ('-fecha',)
