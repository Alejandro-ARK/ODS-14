from django import forms

from .models import MAX_PREGUNTAS, MAX_SEGUNDOS, MIN_PREGUNTAS, MIN_SEGUNDOS, Pregunta


class CrearSalaForm(forms.Form):
    """RF-02: entre 5 y 15 preguntas, entre 10 y 30 segundos por pregunta."""
    cantidad = forms.IntegerField(
        label='Número de preguntas', min_value=MIN_PREGUNTAS, max_value=MAX_PREGUNTAS, initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))
    segundos = forms.IntegerField(
        label='Segundos por pregunta', min_value=MIN_SEGUNDOS, max_value=MAX_SEGUNDOS, initial=20,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))

    def clean_cantidad(self):
        cantidad = self.cleaned_data['cantidad']
        disponibles = Pregunta.objects.filter(activa=True).count()
        if cantidad > disponibles:
            raise forms.ValidationError(f'El banco solo tiene {disponibles} preguntas activas.')
        return cantidad


class PinForm(forms.Form):
    """Alternativa al QR: escribir el PIN de 6 dígitos."""
    pin = forms.RegexField(
        label='PIN de la sala', regex=r'^\d{6}$',
        error_messages={'invalid': 'El PIN tiene 6 dígitos.'},
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg text-center mo-pin-input',
                                      'inputmode': 'numeric', 'autocomplete': 'off',
                                      'maxlength': 6, 'placeholder': '000000'}))
