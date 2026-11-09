"""CU-08: webhook del Steam simulado y API JSON de la pantalla de ventas."""

import hmac
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from usuarios.composition import crear_acceso_service
from usuarios.exceptions import RolNoAutorizadoError, UsuarioError
from usuarios.exceptions import UsuarioInactivoError
from ventas.composition import crear_ventas_service, token_steam
from ventas.exceptions import (
    VentaDuplicadaError,
    VentaNoEncontradaError,
    VentasError,
)
from ventas.forms import (
    ConciliacionVentasForm,
    EventoSteamForm,
    FiltroVentasForm,
)

SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)


def _error(mensaje, status, **extra):
    return JsonResponse({"error": mensaje, **extra}, status=status)


def _autorizado(request):
    token = token_steam()
    recibido = request.headers.get("Authorization", "")
    return bool(token) and hmac.compare_digest(recibido, f"Bearer {token}")


def verificar_modulo(request, modulo):
    try:
        crear_acceso_service().verificar_acceso(request.user, modulo)
    except UsuarioError as error:
        return _error(str(error), 403)
    return None


def venta_json(venta):
    return {
        "id": venta.identificador, "date": venta.fecha.isoformat(),
        "time": venta.fecha_hora.isoformat(), "title": venta.titulo,
        "type": venta.get_tipo_producto_display(), "channel": "Steam",
        "status": venta.get_estado_display(), "amount": str(venta.total),
        "quantity": venta.cantidad, "unitPrice": str(venta.precio_unitario),
        "currency": venta.moneda, "country": venta.pais,
        "commission": str(venta.comision), "tax": str(venta.impuesto),
        "net": str(venta.neto),
        "correlativo": (f"Transacción {venta.transaccion_id}"
                        if venta.transaccion_id else ""),
    }


@csrf_exempt
@require_POST
def steam_ventas(request):
    """CU-08.4: recibe un evento de venta del servicio Steam simulado."""
    if not token_steam():
        return _error("El token del simulador no está configurado.", 503)
    if not _autorizado(request):
        return _error("No autorizado.", 401)
    servicio = crear_ventas_service()
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict):
            raise ValueError
    except ValueError:
        servicio.registrar_error("", "El cuerpo no es un JSON válido.")
        return _error("El cuerpo no es un JSON válido.", 400)
    form = EventoSteamForm(datos)
    if not form.is_valid():
        detalle = "; ".join(f"{campo}: {' '.join(errores)}"
                            for campo, errores in form.errors.items())
        servicio.registrar_error(str(datos.get("id", ""))[:64], detalle)
        return _error("Evento inválido.", 422, campos=form.errors)
    try:
        venta = servicio.recibir(**form.datos_servicio())
    except VentaDuplicadaError as error:
        return _error(str(error), 409)
    except VentasError as error:
        return _error(str(error), 422)
    return JsonResponse({"id": venta.identificador,
                         "estado": venta.get_estado_display()}, status=201)


@csrf_exempt
@require_POST
def steam_latido(request):
    if not token_steam():
        return _error("El token del simulador no está configurado.", 503)
    if not _autorizado(request):
        return _error("No autorizado.", 401)
    crear_ventas_service().latido()
    return JsonResponse({"estado": "Conectado"})


@login_required
@require_GET
def ventas_api(request):
    if (denegado := verificar_modulo(request, "operations")):
        return denegado
    form = FiltroVentasForm(request.GET)
    if not form.is_valid():
        return _error("Filtro inválido.", 400, campos=form.errors)
    servicio = crear_ventas_service()
    try:
        ventas = servicio.listar(
            request.user, consulta=form.cleaned_data["q"],
            desde=form.cleaned_data["desde"],
            hasta=form.cleaned_data["hasta"],
        )
    except SIN_PERMISO as error:
        return _error(str(error), 403)
    conexion = servicio.estado_conexion()
    return JsonResponse({
        "ventas": [venta_json(v) for v in ventas],
        "puedeContabilizar": servicio.puede_contabilizar(request.user),
        "conexion": {
            "estado": conexion.estado,
            "ultimoContacto": (conexion.ultimo_contacto.isoformat()
                               if conexion.ultimo_contacto else None),
            "ultimoError": (conexion.ultimo_error.isoformat()
                            if conexion.ultimo_error else None),
        },
    })


@login_required
@require_http_methods(["GET", "POST"])
def conciliacion_api(request):
    """Previsualiza y confirma la conciliación de eventos Steam."""
    if (denegado := verificar_modulo(request, "operations")):
        return denegado
    datos = request.GET if request.method == "GET" else request.POST
    form = ConciliacionVentasForm(datos)
    if not form.is_valid():
        return _error("Indica un período válido.", 400,
                      campos=form.errors)
    servicio = crear_ventas_service()
    desde, hasta = (form.cleaned_data["desde"],
                    form.cleaned_data["hasta"])
    try:
        if request.method == "GET":
            resumen = servicio.previsualizar_conciliacion(
                request.user, desde, hasta
            )
            return JsonResponse({
                "eventos": resumen.eventos,
                "total": str(resumen.total),
                "cuentasPorCobrar": str(resumen.cuentas_por_cobrar),
                "comision": str(resumen.comision),
            })
        resultado = servicio.conciliar(request.user, desde, hasta)
    except SIN_PERMISO as error:
        return _error(str(error), 403)
    except VentasError as error:
        return _error(str(error), 422)
    return JsonResponse({
        "conciliadas": resultado.conciliadas,
        "total": str(resultado.total),
        "cuentasPorCobrar": str(resultado.cuentas_por_cobrar),
        "comision": str(resultado.comision),
        "errores": list(resultado.errores),
    })


@login_required
@require_POST
def contabilizar_api(request, identificador):
    if (denegado := verificar_modulo(request, "operations")):
        return denegado
    try:
        venta = crear_ventas_service().contabilizar(request.user,
                                                    identificador)
    except SIN_PERMISO as error:
        return _error(str(error), 403)
    except VentaNoEncontradaError as error:
        return _error(str(error), 404)
    except VentasError as error:
        return _error(str(error), 422)
    return JsonResponse({
        "mensaje": f"Venta {venta.identificador} registrada en el Libro "
                   f"Mayor (transacción {venta.transaccion_id}).",
        "venta": venta_json(venta),
    })
