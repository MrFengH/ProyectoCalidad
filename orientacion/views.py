import datetime
import json

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView

from . import services
from .decorators import role_required
from .forms import (
    CancelarCitaForm, CerrarCicloForm, CitaEstudianteForm, CitaStaffForm,
    ExpedienteForm, LoginForm, PsicologoCreateForm, RegistroEstudianteForm,
    RegistroForm,
)
from .models import (
    HORAS, ROL_DIRECTORA, ROL_ESTUDIANTE, ROLES_STAFF, Cita, Disponibilidad,
    Expediente, Registro, Usuario,
)
from .nav import nav_items_for, page_title


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

class SopLoginView(LoginView):
    template_name = 'orientacion/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['register_form'] = RegistroEstudianteForm()
        return ctx


class SopLogoutView(LogoutView):
    next_page = reverse_lazy('login')


class RegistroEstudianteView(FormView):
    """Alta de cuenta propia de estudiante, mostrada en el mismo login."""
    template_name = 'orientacion/login.html'
    form_class = RegistroEstudianteForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        data = form.cleaned_data
        usuario = Usuario.objects.create_user(
            cedula=data['cedula'], nombre=data['nombre'], password=data['password'],
            rol=ROL_ESTUDIANTE, correo=data['correo'],
        )
        Expediente.objects.get_or_create(estudiante=usuario)
        messages.success(self.request, 'Cuenta creada. Ya puedes iniciar sesión.')
        return redirect('login')

    def form_invalid(self, form):
        return render(self.request, self.template_name, {
            'form': LoginForm(), 'register_form': form, 'show_register': True,
        })


# ---------------------------------------------------------------------------
# Estructura compartida (encabezado, barra lateral, estadísticas)
# ---------------------------------------------------------------------------

def shell_context(request, page_id):
    titulo, sub = page_title(page_id, request.user.rol)
    return {
        'nav_items': nav_items_for(request.user.rol),
        'page_id': page_id,
        'page_title': titulo,
        'page_sub': sub,
        'stats': services.stats_for(request.user),
        'institucion': 'UTP',
    }


# ---------------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------------

@role_required('inicio')
def inicio_view(request):
    user = request.user
    is_est = user.rol == ROL_ESTUDIANTE
    hoy = datetime.date.today()

    if is_est:
        mensaje = 'Aquí puedes agendar tus citas de orientación y revisar su estado en cualquier momento.'
        citas_qs = Cita.objects.filter(estudiante=user)
    elif user.rol == ROL_DIRECTORA:
        mensaje = 'Supervisa la operación del servicio, revisa expedientes y administra las cuentas del personal.'
        citas_qs = Cita.objects.all()
    else:
        mensaje = 'Gestiona tu disponibilidad, atiende las citas y mantén al día los expedientes de los estudiantes.'
        citas_qs = Cita.objects.all()

    proximas = (citas_qs.filter(estado=Cita.ESTADO_AGENDADA, fecha__gte=hoy)
                .order_by('fecha', 'hora')[:5])
    shortcuts = [n for n in nav_items_for(user.rol) if n['id'] != 'inicio']

    ctx = shell_context(request, 'inicio')
    ctx.update({
        'saludo': f'Hola, {user.nombre}',
        'mensaje': mensaje,
        'shortcuts': shortcuts,
        'proximas': proximas,
        'hoy': hoy,
    })
    return render(request, 'orientacion/inicio.html', ctx)


# ---------------------------------------------------------------------------
# Agendar cita
# ---------------------------------------------------------------------------

def _slot_choices(hoy):
    fechas = services.fechas_con_cupo(hoy)
    fecha_choices = [('', 'Seleccione una fecha')] + [
        (f.isoformat(), f'{services.wname(f)} {f.strftime("%d/%m/%Y")}') for f in fechas
    ]
    horas_por_fecha = {f.isoformat(): services.free_horas(f) for f in fechas}
    return fecha_choices, horas_por_fecha


@role_required('agenda')
def agenda_view(request):
    user = request.user
    is_est = user.rol == ROL_ESTUDIANTE
    hoy = datetime.date.today()
    fecha_choices, horas_por_fecha = _slot_choices(hoy)

    fecha_sel = request.POST.get('fecha') or request.GET.get('fecha') or ''
    hora_choices = [('', 'Seleccione fecha primero')]
    if fecha_sel and fecha_sel in horas_por_fecha:
        hora_choices = [('', 'Seleccione hora')] + [(h, h) for h in horas_por_fecha[fecha_sel]]

    form_class = CitaEstudianteForm if is_est else CitaStaffForm

    if request.method == 'POST':
        form = form_class(request.POST, fechas=fecha_choices, horas=hora_choices)
        if form.is_valid():
            fecha = datetime.date.fromisoformat(form.cleaned_data['fecha'])
            hora = form.cleaned_data['hora']
            motivo = form.cleaned_data['motivo']
            if hora not in services.free_horas(fecha):
                messages.error(request, 'Ese horario ya está ocupado.')
            else:
                if is_est:
                    estudiante = user
                else:
                    estudiante = services.get_or_create_estudiante(
                        form.cleaned_data['cedula'].strip(), form.cleaned_data['nombre'].strip())
                Cita.objects.create(estudiante=estudiante, fecha=fecha, hora=hora, motivo=motivo)
                messages.success(request, 'Cita agendada correctamente')
                return redirect('agenda')
        else:
            messages.error(request, 'Complete todos los campos de la cita')
    else:
        form = form_class(fechas=fecha_choices, horas=hora_choices, initial={'fecha': fecha_sel})

    if is_est:
        mis_citas = Cita.objects.filter(estudiante=user).order_by('fecha', 'hora')
        citas_titulo, citas_sub = 'Mis citas', 'Todas tus citas agendadas y atendidas.'
    else:
        mis_citas = Cita.objects.filter(estado=Cita.ESTADO_AGENDADA).order_by('fecha', 'hora')
        citas_titulo, citas_sub = 'Próximas citas', 'Citas activas ordenadas por fecha.'

    disponibilidad_json = json.dumps(
        [[f.isoformat(), h] for f, h in Disponibilidad.objects.values_list('fecha', 'hora')])
    citas_agendadas_json = json.dumps(
        [[f.isoformat(), h] for f, h in
         Cita.objects.filter(estado=Cita.ESTADO_AGENDADA).values_list('fecha', 'hora')])

    ctx = shell_context(request, 'agenda')
    ctx.update({
        'form': form,
        'is_est': is_est,
        'mis_citas': mis_citas,
        'citas_titulo': citas_titulo,
        'citas_sub': citas_sub,
        'horas_por_fecha_json': json.dumps(horas_por_fecha),
        'disponibilidad_json': disponibilidad_json,
        'citas_agendadas_json': citas_agendadas_json,
        'horas_json': json.dumps(HORAS),
    })
    return render(request, 'orientacion/agenda.html', ctx)


@role_required('agenda')
def agenda_cancelar_view(request, pk):
    cita = get_object_or_404(Cita, pk=pk, estudiante=request.user)
    if cita.estado != Cita.ESTADO_AGENDADA:
        return redirect('agenda')
    if request.method == 'POST':
        form = CancelarCitaForm(request.POST)
        if form.is_valid():
            cita.estado = Cita.ESTADO_CANCELADA
            cita.motivo_cancelacion = form.cleaned_data['motivo_cancelacion']
            cita.save(update_fields=['estado', 'motivo_cancelacion'])
            messages.success(request, 'Cita cancelada')
            return redirect('agenda')
    else:
        form = CancelarCitaForm()
    ctx = shell_context(request, 'agenda')
    ctx.update({'cita': cita, 'form': form, 'volver_url': reverse_lazy('agenda')})
    return render(request, 'orientacion/cancelar_cita.html', ctx)


# ---------------------------------------------------------------------------
# Calendario de disponibilidad
# ---------------------------------------------------------------------------

@role_required('calendario')
def calendario_view(request):
    semana_param = request.GET.get('semana')
    try:
        ref = datetime.date.fromisoformat(semana_param) if semana_param else datetime.date.today()
    except ValueError:
        ref = datetime.date.today()
    lunes = services.lunes(ref)
    dias = services.dias_semana(lunes)

    citas_ocupadas = set(
        Cita.objects.filter(fecha__in=dias, estado=Cita.ESTADO_AGENDADA).values_list('fecha', 'hora'))
    disp_set = set(Disponibilidad.objects.filter(fecha__in=dias).values_list('fecha', 'hora'))

    filas = []
    for hora in HORAS:
        celdas = []
        for f in dias:
            ocupada = (f, hora) in citas_ocupadas
            disponible = (f, hora) in disp_set
            celdas.append({'fecha': f, 'hora': hora, 'ocupada': ocupada, 'disponible': disponible})
        filas.append({'hora': hora, 'celdas': celdas})

    citas_ocupadas_all = set(Cita.objects.filter(estado=Cita.ESTADO_AGENDADA).values_list('fecha', 'hora'))
    disp_list_qs = Disponibilidad.objects.order_by('fecha', 'hora')
    disp_list = [{
        'obj': d, 'fecha': d.fecha, 'hora': d.hora,
        'ocupada': (d.fecha, d.hora) in citas_ocupadas_all,
    } for d in disp_list_qs]

    ctx = shell_context(request, 'calendario')
    ctx.update({
        'dias': dias,
        'filas': filas,
        'semana': lunes,
        'semana_prev': lunes - datetime.timedelta(days=7),
        'semana_next': lunes + datetime.timedelta(days=7),
        'disp_list': disp_list,
    })
    return render(request, 'orientacion/calendario.html', ctx)


@role_required('calendario')
def calendario_toggle_view(request):
    if request.method != 'POST':
        return redirect('calendario')
    fecha = datetime.date.fromisoformat(request.POST['fecha'])
    hora = request.POST['hora']
    semana = request.POST.get('semana', '')
    ocupada = Cita.objects.filter(fecha=fecha, hora=hora, estado=Cita.ESTADO_AGENDADA).exists()
    if ocupada:
        messages.warning(request, 'Ese horario ya tiene una cita agendada')
    else:
        existente = Disponibilidad.objects.filter(fecha=fecha, hora=hora).first()
        if existente:
            existente.delete()
            messages.success(request, 'Disponibilidad eliminada')
        else:
            Disponibilidad.objects.create(fecha=fecha, hora=hora, psicologo=request.user)
            messages.success(request, 'Disponibilidad agregada')
    url = reverse_lazy('calendario')
    return redirect(f'{url}?semana={semana}' if semana else url)


@role_required('calendario')
def calendario_eliminar_view(request, pk):
    if request.method != 'POST':
        return redirect('calendario')
    disp = get_object_or_404(Disponibilidad, pk=pk)
    ocupada = Cita.objects.filter(fecha=disp.fecha, hora=disp.hora, estado=Cita.ESTADO_AGENDADA).exists()
    if ocupada:
        messages.warning(request, 'Ese horario ya tiene una cita agendada')
    else:
        disp.delete()
        messages.success(request, 'Disponibilidad eliminada')
    return redirect('calendario')


# ---------------------------------------------------------------------------
# Gestionar citas
# ---------------------------------------------------------------------------

@role_required('gestionCitas')
def gestion_citas_view(request):
    citas = Cita.objects.select_related('estudiante').order_by('fecha', 'hora')
    ctx = shell_context(request, 'gestionCitas')
    ctx['citas'] = citas
    return render(request, 'orientacion/gestion_citas.html', ctx)


@role_required('gestionCitas')
def gestion_citas_cerrar_view(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.estado != Cita.ESTADO_AGENDADA:
        return redirect('gestion_citas')
    if request.method == 'POST':
        form = CerrarCicloForm(request.POST)
        if form.is_valid():
            cita.estado = Cita.ESTADO_ATENDIDA
            cita.psicologo = request.user
            cita.save(update_fields=['estado', 'psicologo'])
            Registro.objects.create(
                cita=cita, estudiante=cita.estudiante, descripcion=form.cleaned_data['descripcion'],
                psicologo=request.user,
            )
            Disponibilidad.objects.filter(fecha=cita.fecha, hora=cita.hora).delete()
            messages.success(request, 'Cita atendida y registro creado')
            return redirect('gestion_citas')
    else:
        form = CerrarCicloForm()
    ctx = shell_context(request, 'gestionCitas')
    ctx.update({'cita': cita, 'form': form})
    return render(request, 'orientacion/cerrar_ciclo.html', ctx)


@role_required('gestionCitas')
def gestion_citas_cancelar_view(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.estado != Cita.ESTADO_AGENDADA:
        return redirect('gestion_citas')
    if request.method == 'POST':
        form = CancelarCitaForm(request.POST)
        if form.is_valid():
            cita.estado = Cita.ESTADO_CANCELADA
            cita.motivo_cancelacion = form.cleaned_data['motivo_cancelacion']
            cita.save(update_fields=['estado', 'motivo_cancelacion'])
            messages.success(request, 'Cita cancelada')
            return redirect('gestion_citas')
    else:
        form = CancelarCitaForm()
    ctx = shell_context(request, 'gestionCitas')
    ctx.update({'cita': cita, 'form': form, 'volver_url': reverse_lazy('gestion_citas')})
    return render(request, 'orientacion/cancelar_cita.html', ctx)


# ---------------------------------------------------------------------------
# Expedientes
# ---------------------------------------------------------------------------

@role_required('expedientes')
def expedientes_view(request, cedula=None):
    estudiantes = Usuario.objects.filter(rol=ROL_ESTUDIANTE).order_by('nombre')
    lista = [{
        'cedula': e.cedula, 'nombre': e.nombre,
        'n_citas': Cita.objects.filter(estudiante=e).count(),
        'n_regs': Registro.objects.filter(estudiante=e).count(),
    } for e in estudiantes]

    seleccionado = None
    form = None
    historial = []
    registros = []
    if cedula:
        seleccionado = get_object_or_404(Usuario, cedula=cedula, rol=ROL_ESTUDIANTE)
        expediente, _ = Expediente.objects.get_or_create(estudiante=seleccionado)
        if request.method == 'POST':
            form = ExpedienteForm(request.POST, instance=expediente)
            if form.is_valid():
                form.save()
                seleccionado.correo = form.cleaned_data['correo']
                seleccionado.save(update_fields=['correo'])
                messages.success(request, 'Expediente actualizado')
                return redirect('expedientes_detalle', cedula=cedula)
        else:
            form = ExpedienteForm(instance=expediente, initial={'correo': seleccionado.correo})
        historial = Cita.objects.filter(estudiante=seleccionado).order_by('-fecha', '-hora')
        registros = Registro.objects.filter(estudiante=seleccionado).order_by('-fecha')

    ctx = shell_context(request, 'expedientes')
    ctx.update({
        'lista': lista, 'seleccionado': seleccionado, 'form': form,
        'historial': historial, 'registros': registros,
    })
    return render(request, 'orientacion/expedientes.html', ctx)


# ---------------------------------------------------------------------------
# Registros de atención
# ---------------------------------------------------------------------------

@role_required('registros')
def registros_view(request):
    editar_id = request.GET.get('editar') or request.POST.get('editar_id')
    editando = None
    if editar_id:
        editando = get_object_or_404(Registro, pk=editar_id)

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            estudiante = services.get_or_create_estudiante(
                form.cleaned_data['cedula'].strip(), form.cleaned_data['estudiante'].strip())
            if editando:
                editando.estudiante = estudiante
                editando.descripcion = form.cleaned_data['descripcion']
                editando.save(update_fields=['estudiante', 'descripcion'])
                messages.success(request, 'Registro actualizado')
            else:
                Registro.objects.create(
                    estudiante=estudiante, descripcion=form.cleaned_data['descripcion'], psicologo=request.user)
                messages.success(request, 'Registro guardado')
            return redirect('registros')
    elif editando:
        form = RegistroForm(initial={
            'estudiante': editando.estudiante.nombre, 'cedula': editando.estudiante.cedula,
            'descripcion': editando.descripcion,
        })
    else:
        form = RegistroForm()

    registros = Registro.objects.select_related('estudiante').order_by('-fecha')
    ctx = shell_context(request, 'registros')
    ctx.update({'form': form, 'registros': registros, 'editando': editando})
    return render(request, 'orientacion/registros.html', ctx)


# ---------------------------------------------------------------------------
# Credenciales (alta de personal)
# ---------------------------------------------------------------------------

@role_required('credenciales')
def credenciales_view(request):
    if request.method == 'POST':
        form = PsicologoCreateForm(request.POST)
        if form.is_valid():
            password = services.gen_password()
            Usuario.objects.create_user(
                cedula=form.cleaned_data['cedula'], nombre=form.cleaned_data['nombre'],
                password=password, rol='psicologo', correo=form.cleaned_data['correo'],
            )
            messages.success(
                request,
                f"Psicólogo registrado · Cédula {form.cleaned_data['cedula']} · Contraseña {password}")
            return redirect('credenciales')
    else:
        form = PsicologoCreateForm()

    staff = Usuario.objects.filter(rol__in=ROLES_STAFF).order_by('nombre')
    ctx = shell_context(request, 'credenciales')
    ctx.update({'form': form, 'staff': staff})
    return render(request, 'orientacion/credenciales.html', ctx)


@role_required('credenciales')
def credenciales_eliminar_view(request, pk):
    if request.method != 'POST':
        return redirect('credenciales')
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta')
    else:
        usuario.delete()
        messages.success(request, 'Usuario eliminado')
    return redirect('credenciales')
