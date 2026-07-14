from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


# Horas fijas en que se pueden ofrecer citas (igual que HORAS en el prototipo original).
HORAS = ['08:00', '09:00', '10:00', '11:00', '14:00', '15:00', '16:00']
HORA_CHOICES = [(h, h) for h in HORAS]

ROL_ESTUDIANTE = 'estudiante'
ROL_PSICOLOGO = 'psicologo'
ROL_DIRECTORA = 'directora'
ROL_CHOICES = [
    (ROL_ESTUDIANTE, 'Estudiante'),
    (ROL_PSICOLOGO, 'Psicólogo'),
    (ROL_DIRECTORA, 'Directora'),
]
# Roles que pueden operar como personal (agendar por un estudiante, atender citas, etc.)
ROLES_STAFF = [ROL_PSICOLOGO, ROL_DIRECTORA]


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, cedula, nombre, password, rol, correo='', **extra_fields):
        if not cedula:
            raise ValueError('La cédula es obligatoria')
        if not nombre:
            raise ValueError('El nombre es obligatorio')
        usuario = self.model(cedula=cedula, nombre=nombre, rol=rol, correo=self.normalize_email(correo) or '', **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, cedula, nombre, password=None, rol=ROL_ESTUDIANTE, correo='', **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(cedula, nombre, password, rol, correo, **extra_fields)

    def create_superuser(self, cedula, nombre, password=None, rol=ROL_DIRECTORA, correo='', **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True')
        return self._create_user(cedula, nombre, password, rol, correo, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Cuenta del sistema. El inicio de sesión se hace por cédula, no por username."""
    cedula = models.CharField('cédula', max_length=20, unique=True)
    nombre = models.CharField('nombre completo', max_length=150)
    correo = models.EmailField('correo', blank=True)
    rol = models.CharField(max_length=12, choices=ROL_CHOICES, default=ROL_ESTUDIANTE)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField('fecha de alta', auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'cedula'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.cedula})'

    def get_full_name(self):
        return self.nombre

    def get_short_name(self):
        return self.nombre

    @property
    def es_estudiante(self):
        return self.rol == ROL_ESTUDIANTE

    @property
    def es_staff_psicologia(self):
        return self.rol in ROLES_STAFF


class Expediente(models.Model):
    """Ficha ampliada de un estudiante: datos de contacto y notas del orientador."""
    estudiante = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name='expediente',
        limit_choices_to={'rol': ROL_ESTUDIANTE},
    )
    telefono = models.CharField('teléfono', max_length=30, blank=True)
    notas = models.TextField('notas del orientador', blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Expediente de {self.estudiante.nombre}'


class Disponibilidad(models.Model):
    """Bloque de horario que el orientador ofrece para agendar citas."""
    fecha = models.DateField()
    hora = models.CharField(max_length=5, choices=HORA_CHOICES)
    psicologo = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='disponibilidades',
        limit_choices_to={'rol__in': ROLES_STAFF}, null=True, blank=True,
    )

    class Meta:
        ordering = ['fecha', 'hora']
        unique_together = ('fecha', 'hora')
        verbose_name = 'disponibilidad'
        verbose_name_plural = 'disponibilidad'

    def __str__(self):
        return f'{self.fecha} {self.hora}'


class Cita(models.Model):
    ESTADO_AGENDADA = 'Agendada'
    ESTADO_ATENDIDA = 'Atendida'
    ESTADO_CANCELADA = 'Cancelada'
    ESTADO_CHOICES = [
        (ESTADO_AGENDADA, 'Agendada'),
        (ESTADO_ATENDIDA, 'Atendida'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    estudiante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='citas_estudiante',
        limit_choices_to={'rol': ROL_ESTUDIANTE},
    )
    fecha = models.DateField()
    hora = models.CharField(max_length=5, choices=HORA_CHOICES)
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_AGENDADA)
    motivo_cancelacion = models.TextField('motivo de la cancelación', blank=True)
    psicologo = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, related_name='citas_atendidas',
        limit_choices_to={'rol__in': ROLES_STAFF}, null=True, blank=True,
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'hora']

    def __str__(self):
        return f'{self.estudiante.nombre} · {self.fecha} {self.hora} ({self.estado})'


class Registro(models.Model):
    """Registro de atención: documenta lo trabajado en una sesión."""
    cita = models.ForeignKey(Cita, on_delete=models.SET_NULL, related_name='registros', null=True, blank=True)
    estudiante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='registros',
        limit_choices_to={'rol': ROL_ESTUDIANTE},
    )
    descripcion = models.TextField()
    psicologo = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, related_name='registros_realizados',
        limit_choices_to={'rol__in': ROLES_STAFF}, null=True, blank=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'Registro de {self.estudiante.nombre} · {self.fecha:%d/%m/%Y}'
