from django import template

register = template.Library()

_ESTADO_CLASSES = {
    'Agendada': 'badge-agendada',
    'Atendida': 'badge-atendida',
    'Cancelada': 'badge-cancelada',
    'Disponible': 'badge-disponible',
    'Ocupada': 'badge-ocupada',
}

_ROL_CLASSES = {
    'directora': 'badge-rol-directora',
    'psicologo': 'badge-rol-psicologo',
    'estudiante': 'badge-rol-estudiante',
}
_ROL_LABELS = {
    'directora': 'Directora',
    'psicologo': 'Psicólogo',
    'estudiante': 'Estudiante',
}


@register.filter
def badge_class(estado):
    return 'badge ' + _ESTADO_CLASSES.get(estado, 'badge-cancelada')


@register.filter
def rol_badge_class(rol):
    return 'badge badge-rol ' + _ROL_CLASSES.get(rol, '')


@register.filter
def rol_label(rol):
    return _ROL_LABELS.get(rol, rol)


@register.filter
def initial(nombre):
    nombre = (nombre or '?').strip()
    return nombre[0].upper() if nombre else '?'


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
