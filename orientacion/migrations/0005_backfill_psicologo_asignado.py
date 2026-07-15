import random

from django.db import migrations


def asignar_psicologos_existentes(apps, schema_editor):
    """Backfill de una sola vez: a los expedientes creados antes de que existiera este
    campo (por lo tanto con psicologo_asignado nulo) se les asigna un psicólogo activo
    al azar, igual que ocurre para los expedientes nuevos."""
    Expediente = apps.get_model('orientacion', 'Expediente')
    Usuario = apps.get_model('orientacion', 'Usuario')

    psicologos = list(Usuario.objects.filter(rol='psicologo', is_active=True))
    if not psicologos:
        return

    for expediente in Expediente.objects.filter(psicologo_asignado__isnull=True):
        expediente.psicologo_asignado = random.choice(psicologos)
        expediente.save(update_fields=['psicologo_asignado'])


def revertir(apps, schema_editor):
    """No hay nada que revertir: dejar el campo en null es una operación válida."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('orientacion', '0004_expediente_psicologo_asignado'),
    ]

    operations = [
        migrations.RunPython(asignar_psicologos_existentes, revertir),
    ]
