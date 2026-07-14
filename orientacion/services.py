"""Utilidades de dominio: fechas de la semana laboral, horas libres y estadísticas
del panel de inicio (equivalentes a las funciones de fecha y renderStats de app.js)."""

import datetime
import secrets

from .models import (
    ROL_ESTUDIANTE, Cita, Disponibilidad, Expediente, Registro, Usuario,
)

DIAS_SEMANA_LABELS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']


def lunes(fecha):
    """Devuelve el lunes de la semana que contiene `fecha`."""
    return fecha - datetime.timedelta(days=fecha.weekday())


def dias_semana(lunes_fecha):
    """Los 5 días hábiles (lunes a viernes) de la semana que empieza en `lunes_fecha`."""
    return [lunes_fecha + datetime.timedelta(days=i) for i in range(5)]


def wname(fecha):
    return DIAS_SEMANA_LABELS[(fecha.weekday() + 1) % 7]


def free_horas(fecha):
    """Horas ofrecidas ese día que no tienen ya una cita Agendada."""
    ocupadas = set(Cita.objects.filter(fecha=fecha, estado=Cita.ESTADO_AGENDADA).values_list('hora', flat=True))
    disponibles = Disponibilidad.objects.filter(fecha=fecha).exclude(hora__in=ocupadas).order_by('hora')
    return [d.hora for d in disponibles]


def fechas_con_cupo(desde):
    """Fechas (>= desde) que tienen disponibilidad ofrecida con al menos una hora libre."""
    fechas = Disponibilidad.objects.filter(fecha__gte=desde).values_list('fecha', flat=True).distinct().order_by('fecha')
    return [f for f in fechas if free_horas(f)]


def gen_password():
    """Contraseña temporal legible, igual de simple que el prototipo original."""
    alfabeto = 'abcdefghjkmnpqrstuvwxyz23456789'
    return ''.join(secrets.choice(alfabeto) for _ in range(6))


def get_or_create_estudiante(cedula, nombre, correo=''):
    """Obtiene (o crea sin acceso de login) la cuenta de un estudiante a partir de su
    cédula. El personal puede agendar citas o registros a nombre de estudiantes que
    aún no se han creado una cuenta; se les crea un usuario inactivo para login pero
    con historial real vía llaves foráneas."""
    usuario, created = Usuario.objects.get_or_create(
        cedula=cedula,
        defaults={'nombre': nombre, 'rol': ROL_ESTUDIANTE, 'correo': correo, 'is_active': False},
    )
    if not created and nombre and usuario.nombre != nombre and not usuario.has_usable_password():
        # Solo se autocompleta el nombre si la cuenta fue creada así (sin contraseña propia).
        usuario.nombre = nombre
        usuario.save(update_fields=['nombre'])
    Expediente.objects.get_or_create(estudiante=usuario)
    return usuario


def stats_for(usuario):
    hoy = datetime.date.today()
    if usuario.rol == ROL_ESTUDIANTE:
        mias = Cita.objects.filter(estudiante=usuario)
        proxima = (mias.filter(estado=Cita.ESTADO_AGENDADA, fecha__gte=hoy)
                   .order_by('fecha', 'hora').first())
        return [
            {'label': 'Citas activas', 'value': mias.filter(estado=Cita.ESTADO_AGENDADA).count()},
            {'label': 'Atenciones recibidas', 'value': mias.filter(estado=Cita.ESTADO_ATENDIDA).count()},
            {'label': 'Próxima cita', 'value': proxima.fecha.strftime('%d/%m/%Y') if proxima else '—'},
        ]
    estudiantes = Usuario.objects.filter(rol=ROL_ESTUDIANTE).count()
    return [
        {'label': 'Horas disponibles', 'value': Disponibilidad.objects.count()},
        {'label': 'Citas activas', 'value': Cita.objects.filter(estado=Cita.ESTADO_AGENDADA).count()},
        {'label': 'Atenciones', 'value': Registro.objects.count()},
        {'label': 'Estudiantes', 'value': estudiantes},
    ]
