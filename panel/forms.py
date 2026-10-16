from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from usuarios.models import Usuario


class CrearUsuarioForm(forms.Form):
    """Alta de cuentas desde el panel: usuario normal o superusuario."""

    ROL_USUARIO = 'usuario'
    ROL_SUPERUSUARIO = 'superusuario'

    nombre = forms.CharField(
        label='Nombre de perfil', max_length=60,
        error_messages={'required': 'El nombre de perfil es obligatorio.',
                        'max_length': 'El nombre de perfil es demasiado largo (máximo 60 caracteres).'},
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': 60}),
    )
    correo = forms.EmailField(
        label='Correo electrónico', max_length=255,
        error_messages={'required': 'El correo es obligatorio.',
                        'invalid': 'Ingresa un correo electrónico válido.'},
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'persona@correo.com'}),
    )
    password1 = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    rol = forms.ChoiceField(
        label='Tipo de cuenta',
        choices=[(ROL_USUARIO, 'Usuario normal'),
                 (ROL_SUPERUSUARIO, 'Superusuario (acceso total al panel)')],
        initial=ROL_USUARIO,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    password_admin = forms.CharField(
        label='Tu contraseña (para confirmar)', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise ValidationError('El nombre de perfil es obligatorio.')
        return nombre

    def clean_correo(self):
        correo = self.cleaned_data['correo'].strip().lower()
        if Usuario.objects.filter(correo__iexact=correo).exists():
            raise ValidationError('Ese correo ya está registrado.')
        return correo

    def clean(self):
        datos = super().clean()
        clave, clave2 = datos.get('password1'), datos.get('password2')
        if clave and clave2:
            if clave != clave2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(clave)
                except ValidationError as e:
                    self.add_error('password1', e)

        # Crear un superusuario es una acción sensible: se pide la contraseña de quien la ejecuta.
        if datos.get('rol') == self.ROL_SUPERUSUARIO:
            if not self.actor.check_password(datos.get('password_admin') or ''):
                self.add_error('password_admin', 'Tu contraseña no es correcta.')
        return datos

    def save(self):
        d = self.cleaned_data
        if d['rol'] == self.ROL_SUPERUSUARIO:
            return Usuario.objects.create_superuser(d['correo'], d['password1'], nombre=d['nombre'])
        return Usuario.objects.create_user(d['correo'], d['password1'], nombre=d['nombre'])
