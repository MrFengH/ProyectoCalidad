from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Cita, Disponibilidad, Expediente, Registro, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ['nombre']
    list_display = ['cedula', 'nombre', 'rol', 'correo', 'is_active', 'is_staff']
    list_filter = ['rol', 'is_active']
    search_fields = ['cedula', 'nombre', 'correo']
    fieldsets = (
        (None, {'fields': ('cedula', 'password')}),
        ('Datos personales', {'fields': ('nombre', 'correo', 'rol')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('cedula', 'nombre', 'rol', 'correo', 'password1', 'password2'),
        }),
    )


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'telefono', 'actualizado']
    search_fields = ['estudiante__nombre', 'estudiante__cedula']


@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'hora', 'psicologo']
    list_filter = ['fecha']


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'fecha', 'hora', 'estado', 'psicologo']
    list_filter = ['estado', 'fecha']
    search_fields = ['estudiante__nombre', 'estudiante__cedula']


@admin.register(Registro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'fecha', 'psicologo']
    search_fields = ['estudiante__nombre', 'estudiante__cedula', 'descripcion']
