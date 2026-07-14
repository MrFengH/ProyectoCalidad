# Sistema de Orientación Psicológica — versión Django

Migración a Django del prototipo estático original (`SistemaOrientacion/`, HTML + JS +
`localStorage`). La lógica, los roles y las pantallas son las mismas; ahora los datos
viven en una base de datos real (SQLite) con modelos, autenticación y permisos por rol
manejados por Django.

## Roles

- **Estudiante**: agenda sus propias citas y ve su historial (`Inicio`, `Mis citas`).
- **Psicólogo**: agenda a nombre de estudiantes, administra su disponibilidad semanal,
  atiende citas (cierra el ciclo con un registro), consulta expedientes y registros.
- **Directora**: todo lo anterior, además de gestionar las cuentas del personal
  (`Credenciales`). Su cuenta seed también tiene acceso al panel de administración de
  Django (`/admin/`).

El inicio de sesión es por **cédula** (no username): `Usuario.USERNAME_FIELD = 'cedula'`.

## Modelos (`orientacion/models.py`)

- `Usuario` — usuario personalizado (`AbstractBaseUser`) con `cedula`, `nombre`, `correo`, `rol`.
- `Expediente` — ficha 1-a-1 con un `Usuario` de rol estudiante (teléfono, notas).
- `Disponibilidad` — bloques de horario ofrecidos por el personal.
- `Cita` — cita agendada por un estudiante, con `estado` (Agendada/Atendida/Cancelada).
- `Registro` — registro de atención, opcionalmente ligado a una `Cita`.

## Poner en marcha

```bash
cd SistemaOrientacionDjango
venv\Scripts\activate            # PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt  # ya instalado si usas el venv incluido
python manage.py migrate
python manage.py seed_demo       # crea las 3 cuentas de prueba y disponibilidad de ejemplo
python manage.py runserver
```

Luego abre http://127.0.0.1:8000/

### Cuentas de prueba (creadas por `seed_demo`)

| Rol        | Cédula     | Contraseña |
|------------|------------|------------|
| Directora  | 8-100-100  | dir123     |
| Psicólogo  | 8-200-200  | psi123     |
| Estudiante | 8-300-300  | est123     |

La cuenta de la directora también sirve para entrar a `/admin/`.

## Estructura

```
sistema_orientacion/    # configuración del proyecto (settings, urls raíz)
orientacion/            # app con modelos, vistas, formularios, templates y estáticos
  models.py             # Usuario, Expediente, Disponibilidad, Cita, Registro
  forms.py              # formularios de cada módulo
  views.py              # una vista por página, con control de acceso por rol
  nav.py                # navegación y títulos por rol (equivalente a NAV_DEFS de app.js)
  services.py           # utilidades de fecha, horas libres y estadísticas
  decorators.py         # role_required(page_id)
  templates/orientacion/
  static/css/style.css  # mismo diseño visual del prototipo original
  management/commands/seed_demo.py
```
