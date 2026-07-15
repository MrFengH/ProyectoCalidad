"""Utilidades de dominio: fechas de la semana laboral, horas libres y estadísticas
del panel de inicio (equivalentes a las funciones de fecha y renderStats de app.js)."""

import datetime
import functools
import operator
import secrets

from django.db.models import Q

from .models import (
    HORAS, ROL_ESTUDIANTE, ROL_PSICOLOGO, Cita, Disponibilidad, Expediente, Registro, Usuario,
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


def free_horas(fecha, psicologo=None):
    """Horas ofrecidas ese día (opcionalmente solo por `psicologo`) que no tienen ya una cita Agendada."""
    ocupadas = set(Cita.objects.filter(fecha=fecha, estado=Cita.ESTADO_AGENDADA).values_list('hora', flat=True))
    disponibles = Disponibilidad.objects.filter(fecha=fecha)
    if psicologo is not None:
        disponibles = disponibles.filter(psicologo=psicologo)
    disponibles = disponibles.exclude(hora__in=ocupadas).order_by('hora')
    return [d.hora for d in disponibles]


def fechas_con_cupo(desde, psicologo=None):
    """Fechas (>= desde) que tienen disponibilidad ofrecida (opcionalmente solo por
    `psicologo`) con al menos una hora libre."""
    fechas_qs = Disponibilidad.objects.filter(fecha__gte=desde)
    if psicologo is not None:
        fechas_qs = fechas_qs.filter(psicologo=psicologo)
    fechas = fechas_qs.values_list('fecha', flat=True).distinct().order_by('fecha')
    return [f for f in fechas if free_horas(f, psicologo=psicologo)]


def week_grid(dias, disponibilidad_qs):
    """Construye la grilla Hora x Día del calendario semanal a partir de un queryset de
    Disponibilidad ya filtrado (por ejemplo, solo la de un psicólogo en particular)."""
    citas_ocupadas = set(
        Cita.objects.filter(fecha__in=dias, estado=Cita.ESTADO_AGENDADA).values_list('fecha', 'hora'))
    disp_set = set(disponibilidad_qs.filter(fecha__in=dias).values_list('fecha', 'hora'))
    filas = []
    for hora in HORAS:
        celdas = [{
            'fecha': f, 'hora': hora,
            'ocupada': (f, hora) in citas_ocupadas,
            'disponible': (f, hora) in disp_set,
        } for f in dias]
        filas.append({'hora': hora, 'celdas': celdas})
    return filas


def disp_list_for(disponibilidad_qs):
    """Lista plana (fecha, hora, ocupada) de un queryset de Disponibilidad, para tablas de solo lectura."""
    citas_ocupadas = set(Cita.objects.filter(estado=Cita.ESTADO_AGENDADA).values_list('fecha', 'hora'))
    return [{
        'fecha': d.fecha, 'hora': d.hora,
        'ocupada': (d.fecha, d.hora) in citas_ocupadas,
    } for d in disponibilidad_qs.order_by('fecha', 'hora')]


def citas_de_psicologo(psicologo):
    """Citas atribuibles a un psicólogo: las que ya atendió/cerró, más las agendadas que
    caen en un horario que él mismo ofreció como disponibilidad."""
    slots = list(Disponibilidad.objects.filter(psicologo=psicologo).values_list('fecha', 'hora'))
    q = Q(psicologo=psicologo)
    if slots:
        q |= functools.reduce(
            operator.or_, (Q(fecha=f, hora=h, estado=Cita.ESTADO_AGENDADA) for f, h in slots))
    return Cita.objects.filter(q).select_related('estudiante').distinct().order_by('-fecha', '-hora')


def estudiantes_de_psicologo(psicologo, citas_qs):
    """Estudiantes relacionados con un psicólogo: los que tiene asignados, más los de sus
    citas y los de sus registros de atención."""
    ids = set(Expediente.objects.filter(psicologo_asignado=psicologo).values_list('estudiante_id', flat=True))
    ids |= set(citas_qs.values_list('estudiante_id', flat=True))
    ids |= set(Registro.objects.filter(psicologo=psicologo).values_list('estudiante_id', flat=True))
    return Usuario.objects.filter(id__in=ids).order_by('nombre')


def asignar_psicologo_aleatorio(expediente):
    """Asigna al expediente un psicólogo activo elegido al azar, una sola vez: no hace
    nada si ya tiene uno asignado o si todavía no existe ningún psicólogo registrado."""
    if expediente.psicologo_asignado_id:
        return
    psicologo = Usuario.objects.filter(rol=ROL_PSICOLOGO, is_active=True).order_by('?').first()
    if psicologo:
        expediente.psicologo_asignado = psicologo
        expediente.save(update_fields=['psicologo_asignado'])


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
    expediente, exp_created = Expediente.objects.get_or_create(estudiante=usuario)
    if exp_created:
        asignar_psicologo_aleatorio(expediente)
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
