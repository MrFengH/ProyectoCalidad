import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from orientacion import services
from orientacion.models import Cita, Disponibilidad, Expediente, Registro, Usuario


class Command(BaseCommand):
    help = 'Crea las cuentas y datos de demostración equivalentes al prototipo original (idempotente).'

    @transaction.atomic
    def handle(self, *args, **options):
        directora, creada = self._crear_usuario('8-100-100', 'Ana Rodríguez', 'directora', 'dir123', 'ana.rodriguez@colegio.edu')
        psicologo, _ = self._crear_usuario('8-200-200', 'Carlos Méndez', 'psicologo', 'psi123', 'carlos.mendez@colegio.edu')
        estudiante, _ = self._crear_usuario('8-300-300', 'María Pérez', 'estudiante', 'est123', 'maria.perez@colegio.edu')
        expediente, exp_creado = Expediente.objects.get_or_create(
            estudiante=estudiante, defaults={'telefono': '6000-0000'})
        if exp_creado:
            services.asignar_psicologo_aleatorio(expediente)

        if Disponibilidad.objects.exists():
            self.stdout.write(self.style.WARNING('Ya existe disponibilidad; no se generan más datos de horario.'))
        else:
            disp = []
            agregados, i = 0, 0
            while agregados < 3 and i < 20:
                i += 1
                fecha = datetime.date.today() + datetime.timedelta(days=i)
                if fecha.weekday() < 5:  # lunes(0)..viernes(4)
                    for hora in ['09:00', '10:00', '14:00']:
                        disp.append(Disponibilidad(fecha=fecha, hora=hora, psicologo=psicologo))
                    agregados += 1
            Disponibilidad.objects.bulk_create(disp)

            primera = disp[0]
            if not Cita.objects.filter(estudiante=estudiante, fecha=primera.fecha, hora=primera.hora).exists():
                Cita.objects.create(
                    estudiante=estudiante, fecha=primera.fecha, hora=primera.hora,
                    motivo='Ansiedad ante los exámenes finales', estado=Cita.ESTADO_AGENDADA,
                )

        self.stdout.write(self.style.SUCCESS(
            'Datos de demostración listos.\n'
            '  Directora  -> cédula 8-100-100 / contraseña dir123\n'
            '  Psicólogo  -> cédula 8-200-200 / contraseña psi123\n'
            '  Estudiante -> cédula 8-300-300 / contraseña est123'
        ))

    def _crear_usuario(self, cedula, nombre, rol, password, correo):
        usuario = Usuario.objects.filter(cedula=cedula).first()
        if usuario:
            return usuario, False
        usuario = Usuario.objects.create_user(cedula=cedula, nombre=nombre, password=password, rol=rol, correo=correo)
        if rol == 'directora':
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save(update_fields=['is_staff', 'is_superuser'])
        return usuario, True
