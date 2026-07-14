"""Definición de navegación y accesos por rol (equivalente a NAV_DEFS / BY_ROLE / MODULE_TITLES de app.js)."""

from .models import ROL_DIRECTORA, ROL_ESTUDIANTE, ROL_PSICOLOGO

NAV_DEFS = [
    {'id': 'inicio', 'url': 'inicio', 'label': 'Inicio', 'desc': ''},
    {'id': 'agenda', 'url': 'agenda', 'label': 'Agendar cita', 'label_estudiante': 'Mis citas',
     'desc': 'Registra una cita en un horario disponible'},
    {'id': 'calendario', 'url': 'calendario', 'label': 'Calendario',
     'desc': 'Administra tu disponibilidad semanal'},
    {'id': 'gestionCitas', 'url': 'gestion_citas', 'label': 'Gestionar citas',
     'desc': 'Atiende y da seguimiento a las citas'},
    {'id': 'expedientes', 'url': 'expedientes', 'label': 'Expedientes',
     'desc': 'Consulta el historial de cada estudiante'},
    {'id': 'registros', 'url': 'registros', 'label': 'Registros de atención',
     'desc': 'Documenta las atenciones brindadas'},
    {'id': 'credenciales', 'url': 'credenciales', 'label': 'Credenciales',
     'desc': 'Gestiona las cuentas del personal'},
]
NAV_BY_ID = {n['id']: n for n in NAV_DEFS}

BY_ROLE = {
    ROL_ESTUDIANTE: ['inicio', 'agenda'],
    ROL_PSICOLOGO: ['inicio', 'agenda', 'calendario', 'gestionCitas', 'expedientes', 'registros'],
    ROL_DIRECTORA: ['inicio', 'agenda', 'calendario', 'gestionCitas', 'expedientes', 'registros', 'credenciales'],
}

MODULE_TITLES = {
    'inicio': {'t': 'Panel de inicio', 's': 'Resumen general y accesos rápidos.'},
    'agenda': {'t': 'Agendar cita', 's': 'Registra una cita para un estudiante en un horario disponible.',
               't_estudiante': 'Mis citas', 's_estudiante': 'Agenda una nueva cita y consulta el estado de las tuyas.'},
    'calendario': {'t': 'Calendario de disponibilidad', 's': 'Define las horas en que el orientador puede atender.'},
    'gestionCitas': {'t': 'Gestionar citas', 's': 'Atiende o cancela las citas registradas.'},
    'expedientes': {'t': 'Expedientes de estudiantes', 's': 'Datos, historial de citas y notas de atención de cada estudiante.'},
    'registros': {'t': 'Registros de atención', 's': 'Historial de atenciones que cierran el ciclo de cada cita.'},
    'credenciales': {'t': 'Credenciales', 's': 'Genera cuentas de acceso para el personal de psicología.'},
}


def nav_ids(rol):
    return BY_ROLE.get(rol, [])


def nav_items_for(rol):
    ids = nav_ids(rol)
    items = []
    for nid in ids:
        d = NAV_BY_ID[nid]
        label = d.get('label_estudiante') if (rol == ROL_ESTUDIANTE and 'label_estudiante' in d) else d['label']
        items.append({'id': nid, 'url': d['url'], 'label': label, 'desc': d['desc']})
    return items


def page_title(page_id, rol):
    d = MODULE_TITLES[page_id]
    is_est = rol == ROL_ESTUDIANTE
    titulo = d.get('t_estudiante') if (is_est and 't_estudiante' in d) else d['t']
    sub = d.get('s_estudiante') if (is_est and 's_estudiante' in d) else d['s']
    return titulo, sub
