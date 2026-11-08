"""CU-05 Libro Mayor y CU-05.1 Consultar Saldo de Cuentas."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from libro_mayor.composition import crear_libro_mayor_service
from libro_mayor.exceptions import CampoObligatorioError, LibroMayorError
from libro_mayor.forms import (
    ConsultaMayorForm,
    MovimientoFormSet,
    SaldoForm,
    TransaccionForm,
)
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .pages import contexto_panel

LIBRO_MAYOR_TEMPLATE = "sic_sunGames/libro_mayor.html"
SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)
PREFIJO_MOVIMIENTOS = "mov"


def _sin_permiso(error):
    return PermissionDenied(str(error))


def _asignar_error(error, form):
    campo = error.campo if error.campo in form.fields else None
    form.add_error(campo, str(error))


def _consultar(request, prefijo, form_class, cuentas, consulta):
    """Arma el formulario GET y ejecuta la consulta si se envió."""
    enviado = f"{prefijo}-cuenta" in request.GET
    form = form_class(
        request.GET if enviado else None, prefix=prefijo, cuentas=cuentas
    )
    if not enviado or not form.is_valid():
        return form, None
    try:
        return form, consulta(form.cleaned_data)
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    except LibroMayorError as error:
        _asignar_error(error, form)
        return form, None


def _render(request, servicio, **extra):
    contexto = contexto_panel(request, "ledger")
    try:
        cuentas = servicio.cuentas(request.user)
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    activas = [cuenta for cuenta in cuentas if cuenta.activa]

    def requerir_cuenta(datos):
        if not datos["cuenta"]:
            raise CampoObligatorioError(campo="cuenta")
        return datos["cuenta"]

    consulta_form, consulta = _consultar(
        request, "consulta", ConsultaMayorForm, cuentas,
        lambda d: servicio.consultar(
            request.user, requerir_cuenta(d),
            desde=d["desde"], hasta=d["hasta"],
        ),
    )
    saldo_form, saldo = _consultar(
        request, "saldo", SaldoForm, cuentas,
        lambda d: servicio.saldo(
            request.user, requerir_cuenta(d), d["fecha_corte"]
        ),
    )
    contexto.update(
        puede_registrar=servicio.puede_registrar(request.user),
        form=TransaccionForm(),
        formset=MovimientoFormSet(
            prefix=PREFIJO_MOVIMIENTOS, form_kwargs={"cuentas": activas}
        ),
        consulta_form=consulta_form,
        consulta=consulta,
        saldo_form=saldo_form,
        saldo=saldo,
    )
    contexto.update(extra)
    return render(request, LIBRO_MAYOR_TEMPLATE, contexto)


@login_required
def libro_mayor(request):
    return _render(request, crear_libro_mayor_service())


@login_required
@require_POST
def registrar_transaccion(request):
    servicio = crear_libro_mayor_service()
    try:
        servicio.verificar_registro(request.user)
        cuentas = [c for c in servicio.cuentas(request.user) if c.activa]
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    form = TransaccionForm(request.POST)
    formset = MovimientoFormSet(
        request.POST, prefix=PREFIJO_MOVIMIENTOS,
        form_kwargs={"cuentas": cuentas},
    )
    if form.is_valid() and formset.is_valid():
        usados = [
            (indice, fila.cleaned_data)
            for indice, fila in enumerate(formset.forms) if fila.has_changed()
        ]
        try:
            transaccion = servicio.registrar(
                request.user,
                fecha=form.cleaned_data["fecha"],
                concepto=form.cleaned_data["concepto"],
                movimientos=[datos for _, datos in usados],
            )
        except SIN_PERMISO as error:
            raise _sin_permiso(error) from error
        except LibroMayorError as error:
            if error.lineas:
                for linea in error.lineas:
                    fila = formset.forms[usados[linea][0]]
                    _asignar_error(error, fila)
            else:
                _asignar_error(error, form)
        else:
            messages.success(
                request,
                f"Transacción {transaccion.pk} registrada con "
                f"{len(usados)} movimientos.",
            )
            return redirect("ledger")
    return _render(request, servicio, form=form, formset=formset)
