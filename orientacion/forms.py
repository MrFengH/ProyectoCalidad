from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import HORA_CHOICES, Disponibilidad, Expediente, Registro, Usuario


class LoginForm(AuthenticationForm):
    """Inicio de sesión por cédula y contraseña (AuthenticationForm ya usa
    Usuario.USERNAME_FIELD internamente, aquí solo ajustamos los widgets)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Cédula'
        self.fields['username'].widget.attrs.update({'class': 'field-input', 'placeholder': '8-000-000', 'autofocus': True})
        self.fields['password'].widget.attrs.update({'class': 'field-input', 'placeholder': '••••••••'})

    error_messages = {
        'invalid_login': 'Credenciales incorrectas.',
        'inactive': 'Esta cuenta está inactiva.',
    }


class RegistroEstudianteForm(forms.Form):
    """Alta de cuenta propia de un estudiante (equivalente a form-register)."""
    nombre = forms.CharField(label='Nombre completo', max_length=150,
                              widget=forms.TextInput(attrs={'class': 'field-input'}))
    cedula = forms.CharField(label='Cédula', max_length=20,
                              widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': '8-000-000'}))
    correo = forms.EmailField(label='Correo', required=False,
                               widget=forms.EmailInput(attrs={'class': 'field-input'}))
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'class': 'field-input'}))

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula'].strip()
        if Usuario.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Ya existe una cuenta con esa cédula.')
        return cedula


class CitaEstudianteForm(forms.Form):
    """Agendar cita cuando quien la crea es el propio estudiante."""
    fecha = forms.ChoiceField(label='Fecha disponible', widget=forms.Select(attrs={'class': 'field-select'}))
    hora = forms.ChoiceField(label='Hora', widget=forms.Select(attrs={'class': 'field-select'}))
    motivo = forms.CharField(label='Motivo', widget=forms.Textarea(attrs={'class': 'field-textarea', 'placeholder': 'Describe brevemente el motivo de la cita'}))

    def __init__(self, *args, fechas=(), horas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].choices = fechas
        self.fields['hora'].choices = horas


class CitaStaffForm(CitaEstudianteForm):
    """Agendar cita cuando la registra personal de psicología a nombre de un estudiante."""
    nombre = forms.CharField(label='Nombre del estudiante', max_length=150,
                              widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': 'Nombre completo'}))
    cedula = forms.CharField(label='Cédula', max_length=20,
                              widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': '8-000-000'}))

    field_order = ['nombre', 'cedula', 'fecha', 'hora', 'motivo']


class ExpedienteForm(forms.ModelForm):
    correo = forms.EmailField(label='Correo', required=False, widget=forms.EmailInput(attrs={'class': 'field-input'}))

    class Meta:
        model = Expediente
        fields = ['telefono', 'notas']
        widgets = {
            'telefono': forms.TextInput(attrs={'class': 'field-input'}),
            'notas': forms.Textarea(attrs={'class': 'field-textarea', 'placeholder': 'Observaciones generales, seguimiento, acuerdos…'}),
        }


class RegistroForm(forms.Form):
    """Alta o edición manual de un registro de atención (no ligado a una cita)."""
    estudiante = forms.CharField(label='Estudiante', max_length=150, widget=forms.TextInput(attrs={'class': 'field-input'}))
    cedula = forms.CharField(label='Cédula', max_length=20, widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': '8-000-000'}))
    descripcion = forms.CharField(label='Descripción de la atención', widget=forms.Textarea(attrs={'class': 'field-textarea'}))


class CerrarCicloForm(forms.Form):
    """Cierra el ciclo de una cita: la marca como atendida y crea su registro."""
    descripcion = forms.CharField(
        label='Descripción de la atención brindada',
        widget=forms.Textarea(attrs={'class': 'field-textarea', 'placeholder': '¿Qué se trabajó en la sesión? Acuerdos, seguimiento…'}),
    )


class PsicologoCreateForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=150, widget=forms.TextInput(attrs={'class': 'field-input'}))
    cedula = forms.CharField(label='Cédula', max_length=20, widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': '8-000-000'}))
    correo = forms.EmailField(label='Correo', required=False, widget=forms.EmailInput(attrs={'class': 'field-input'}))

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula'].strip()
        if Usuario.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Ya existe un usuario con esa cédula.')
        return cedula
