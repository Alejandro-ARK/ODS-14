from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import Usuario


# ---------------------------------------------------------------------------
# Formularios del sitio
# ---------------------------------------------------------------------------
class LoginForm(forms.Form):
    correo = forms.CharField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'tu@correo.com', 'autofocus': True,
        }),
    )
    contrasena = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.usuario = None

    def clean(self):
        datos = super().clean()
        correo, clave = datos.get('correo'), datos.get('contrasena')
        if correo and clave:
            self.usuario = authenticate(self.request, username=correo.lower(), password=clave)
            if self.usuario is None:
                raise ValidationError('Correo o contraseña incorrectos.')
        return datos


class RegistroForm(forms.Form):
    """
    Replica las validaciones del register.php original, en el mismo orden y con
    los mismos mensajes. Se valida todo en clean() para mostrar un solo error.
    """
    nombre = forms.CharField(
        label='Nombre de perfil', required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'maxlength': 60,
            'placeholder': '¿Cómo quieres que te llamemos?',
        }),
    )
    correo = forms.CharField(
        label='Correo electrónico', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@correo.com'}),
    )
    contrasena = forms.CharField(
        label='Contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 6 caracteres'}),
    )
    contrasena2 = forms.CharField(
        label='Confirmar contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repite tu contraseña'}),
    )

    def clean(self):
        datos = super().clean()
        nombre = datos.get('nombre', '')
        correo = datos.get('correo', '').lower()
        clave = datos.get('contrasena', '')
        clave2 = datos.get('contrasena2', '')

        if not nombre or not correo or not clave:
            raise ValidationError('Por favor completa todos los campos.')
        try:
            validate_email(correo)
        except ValidationError:
            raise ValidationError('Ingresa un correo electrónico válido.')
        if len(nombre) > 60:
            raise ValidationError('El nombre de perfil es demasiado largo (máximo 60 caracteres).')
        if clave != clave2:
            raise ValidationError('Las contraseñas no coinciden.')
        if len(clave) < 6:
            raise ValidationError('La contraseña debe tener al menos 6 caracteres.')
        if Usuario.objects.filter(correo__iexact=correo).exists():
            raise ValidationError('Ese correo ya está registrado. Intenta iniciar sesión.')

        datos['correo'] = correo
        return datos

    def save(self):
        d = self.cleaned_data
        return Usuario.objects.create_user(correo=d['correo'], password=d['contrasena'], nombre=d['nombre'])


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre']
        widgets = {'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 60})}
        error_messages = {
            'nombre': {
                'required': 'El nombre de perfil no puede estar vacío.',
                'max_length': 'El nombre de perfil es demasiado largo (máximo 60 caracteres).',
            },
        }


# ---------------------------------------------------------------------------
# Formularios del panel de administración (el modelo de usuario es propio, así
# que los formularios por defecto de Django, pensados para "username", no sirven).
# ---------------------------------------------------------------------------
class UsuarioCreationForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ('correo', 'nombre')


class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = '__all__'
