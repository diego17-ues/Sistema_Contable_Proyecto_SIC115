"""CU-08 Verificar Ventas, CU-08.2 Contabilizar y CU-08.4 Conectar con API.

Asiento de cada venta (instrucción de Diego):

    Debe  1104 Cuentas por cobrar a plataformas   total - comisión
    Debe  4302 Comisiones por plataformas         comisión
    Haber 5101 (juego) / 5102 (DLC) Ingresos       total = cantidad × precio

El impuesto informado por Steam se muestra pero no se contabiliza hasta que
exista una tasa configurada (AGENT.md, reglas contables).
"""

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from bitacora.eventos import Accion, Resultado
from libro_mayor.exceptions import LibroMayorError
from libro_mayor.models import TipoMovimiento
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from .exceptions import (
    ContabilizacionError,
    EventoInvalidoError,
    MonedaNoAdmitidaError,
    RangoConciliacionInvalidoError,
    VentaDuplicadaError,
    VentasError,
    VentaYaRegistradaError,
)
from .models import CENTAVO, EstadoVenta, TipoProducto

CERO = Decimal("0.00")


@dataclass(frozen=True)
class ConfiguracionVentas:
    moneda: str = "USD"
    cuenta_por_cobrar: str = "1104"
    cuenta_comision: str = "4302"
    cuenta_ingreso_juego: str = "5101"
    cuenta_ingreso_dlc: str = "5102"
    minutos_conectado: int = 5


@dataclass(frozen=True)
class EstadoConexion:
    estado: str
    ultimo_contacto: datetime = None
    ultimo_error: datetime = None


@dataclass(frozen=True)
class ResumenConciliacion:
    conciliadas: int
    total: Decimal
    cuentas_por_cobrar: Decimal
    comision: Decimal
    errores: tuple = ()


@dataclass(frozen=True)
class VistaPreviaConciliacion:
    eventos: int
    total: Decimal
    cuentas_por_cobrar: Decimal
    comision: Decimal


def _ahora():
    return datetime.now(timezone.utc)


class VentasService:
    ROLES_CONSULTA = frozenset({Rol.CONTADOR_GENERAL, Rol.ADMINISTRADOR})
    ROLES_REGISTRO = frozenset({Rol.CONTADOR_GENERAL})

    def __init__(self, repositorio, mayor, bitacora, configuracion=None,
                 transaccion=nullcontext, reloj=_ahora):
        self._repositorio = repositorio
        self._mayor = mayor
        self._bitacora = bitacora
        self._config = configuracion or ConfiguracionVentas()
        self._transaccion = transaccion
        self._reloj = reloj

    def puede_contabilizar(self, actor):
        return actor.activo and actor.rol in self.ROLES_REGISTRO

    def recibir(self, *, identificador, titulo, tipo_producto, cantidad,
                precio_unitario, moneda, pais, fecha_hora, comision,
                impuesto=CERO):
        """CU-08.4: valida y guarda un evento; queda pendiente de revisión."""
        referencia = f"Steam {identificador}"[:60]
        try:
            moneda = moneda.upper()
            if moneda != self._config.moneda:
                raise MonedaNoAdmitidaError(
                    f"Moneda {moneda} no admitida; solo se reciben ventas en "
                    f"{self._config.moneda}."
                )
            total = (precio_unitario * cantidad).quantize(CENTAVO)
            if comision > total:
                raise EventoInvalidoError(
                    "La comisión supera el total de la venta."
                )
            if self._repositorio.existe(identificador):
                raise VentaDuplicadaError()
            venta = self._repositorio.crear(
                identificador=identificador, titulo=titulo,
                tipo_producto=tipo_producto, cantidad=cantidad,
                precio_unitario=precio_unitario, moneda=moneda,
                pais=pais.upper(), fecha_hora=fecha_hora, comision=comision,
                impuesto=impuesto,
            )
        except VentasError as error:
            with self._transaccion():
                self._repositorio.registrar_error(self._reloj())
                self.rechazar_evento(identificador, str(error))
            raise
        self._bitacora.registrar(
            Accion.RECEPCION_VENTA, Resultado.EXITOSO, referencia=referencia,
            detalle=f"{titulo} · {cantidad} × {precio_unitario} {moneda}",
        )
        return venta

    def rechazar_evento(self, identificador, motivo):
        self._bitacora.registrar(
            Accion.RECEPCION_VENTA, Resultado.RECHAZADO,
            referencia=f"Steam {identificador or '—'}"[:60],
            detalle=motivo[:500],
        )

    def latido(self):
        self._repositorio.registrar_contacto(self._reloj())

    def estado_conexion(self):
        ultimo = self._repositorio.ultimo_contacto()
        ultimo_error = self._repositorio.ultimo_error()
        if ultimo_error and (ultimo is None or ultimo_error >= ultimo):
            return EstadoConexion("Error", ultimo, ultimo_error)
        if ultimo is None:
            return EstadoConexion("En espera")
        limite = timedelta(minutes=self._config.minutos_conectado)
        estado = ("Conectado" if self._reloj() - ultimo <= limite
                  else "Fuera de servicio")
        return EstadoConexion(estado, ultimo)

    def registrar_error(self, identificador=None, motivo=None):
        """Registra el error de una solicitud autenticada del simulador."""
        if motivo is None:
            self._repositorio.registrar_error(self._reloj())
            return
        with self._transaccion():
            self._repositorio.registrar_error(self._reloj())
            self.rechazar_evento(identificador or "", motivo)

    def listar(self, actor, *, consulta="", desde=None, hasta=None):
        self._verificar(actor, self.ROLES_CONSULTA)
        return self._repositorio.listar(
            consulta=(consulta or "").strip(), desde=desde, hasta=hasta
        )

    def pendientes_en(self, desde, hasta):
        return self._repositorio.contar_pendientes(desde, hasta)

    def previsualizar_conciliacion(self, actor, desde, hasta):
        self._verificar(actor, self.ROLES_REGISTRO)
        ventas = self._ventas_para_conciliar(desde, hasta)
        total = sum((venta.total for venta in ventas), CERO)
        comision = sum((venta.comision for venta in ventas), CERO)
        return VistaPreviaConciliacion(
            len(ventas), total, total - comision, comision
        )

    def conciliar(self, actor, desde, hasta):
        """Conciliación repetible; eventos ya registrados no duplican asientos."""
        self._verificar(actor, self.ROLES_REGISTRO)
        ventas = self._ventas_para_conciliar(desde, hasta)
        with self._transaccion():
            conciliadas = 0
            total = CERO
            comision = CERO
            errores = []
            for venta in ventas:
                try:
                    if venta.estado != EstadoVenta.REGISTRADA:
                        self.contabilizar(actor, venta.identificador)
                except VentasError as error:
                    errores.append({
                        "id": venta.identificador,
                        "mensaje": str(error),
                    })
                    continue
                conciliadas += 1
                total += venta.total
                comision += venta.comision

            resultado = (Resultado.RECHAZADO
                         if errores and conciliadas == 0
                         else Resultado.EXITOSO)
            self._bitacora.registrar(
                Accion.CONCILIACION_VENTAS, resultado, actor=actor,
                referencia=f"Steam {desde} a {hasta}"[:60],
                detalle=(f"Conciliadas: {conciliadas}; total: {total:.2f}; "
                         f"cuentas por cobrar: {total - comision:.2f}; "
                         f"comisión: {comision:.2f}; "
                         f"errores: {len(errores)}"),
            )
            return ResumenConciliacion(
                conciliadas, total, total - comision, comision,
                tuple(errores),
            )

    def _ventas_para_conciliar(self, desde, hasta):
        if desde > hasta:
            raise RangoConciliacionInvalidoError()
        return self._repositorio.ventas_en_periodo(desde, hasta)

    def contabilizar(self, actor, identificador):
        """CU-08.2: registra la venta en el Libro Mayor, una sola vez."""
        self._verificar(actor, self.ROLES_REGISTRO)
        venta = self._repositorio.obtener(identificador)
        if venta.transaccion_id:
            raise VentaYaRegistradaError(
                "La venta ya está registrada en la transacción "
                f"{venta.transaccion_id}."
            )
        try:
            if self._mayor.periodo_de(venta.fecha).cerrado:
                raise ContabilizacionError(
                    "El período de la venta está cerrado; no se registra."
                )
            lineas = self._lineas(venta)
            with self._transaccion():
                transaccion = self._mayor.crear_transaccion(usuario=actor)
                for cuenta, importe in lineas:
                    self._mayor.crear_movimiento(
                        transaccion=transaccion, cuenta=cuenta,
                        fecha=venta.fecha,
                        concepto=(f"Venta Steam {venta.identificador} · "
                                  f"{venta.titulo}")[:200],
                        referencia=venta.identificador[:40],
                        tipo=TipoMovimiento.COMPROBANTE_INGRESO,
                        importe=importe,
                    )
                self._repositorio.marcar_registrada(venta, transaccion)
                self._bitacora.registrar(
                    Accion.CONTABILIZACION_VENTA, Resultado.EXITOSO,
                    actor=actor,
                    referencia=(f"Venta {venta.identificador} · "
                                f"transacción {transaccion.pk}")[:60],
                    detalle=" · ".join(
                        f"{c.codigo} {importe:+.2f}" for c, importe in lineas
                    ),
                )
        except LibroMayorError as exc:
            raise ContabilizacionError(str(exc)) from exc
        return venta

    def _lineas(self, venta):
        config = self._config
        ingreso = (config.cuenta_ingreso_dlc
                   if venta.tipo_producto == TipoProducto.DLC
                   else config.cuenta_ingreso_juego)
        lineas = [
            (config.cuenta_por_cobrar, venta.neto),
            (config.cuenta_comision, venta.comision),
            (ingreso, -venta.total),
        ]
        return [(self._cuenta(codigo), importe)
                for codigo, importe in lineas if importe]

    def _cuenta(self, codigo):
        cuenta = self._mayor.obtener_cuenta(codigo)
        if not cuenta.activa or self._mayor.tiene_subcuentas(cuenta):
            raise ContabilizacionError(
                f"La cuenta {codigo} no admite registros."
            )
        return cuenta

    @staticmethod
    def _verificar(actor, roles):
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol not in roles:
            raise RolNoAutorizadoError()
