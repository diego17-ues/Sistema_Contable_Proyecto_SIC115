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
    ConciliacionNoPermitidaError,
    ContabilizacionError,
    EventoInvalidoError,
    MonedaNoAdmitidaError,
    PeriodoYaConciliadoError,
    RangoConciliacionInvalidoError,
    VentaDuplicadaError,
    VentasError,
    VentaYaRegistradaError,
)
from .models import CENTAVO, EstadoVenta, OrigenVenta, TipoProducto

CERO = Decimal("0.00")


@dataclass(frozen=True)
class ConfiguracionVentas:
    moneda: str = "USD"
    cuenta_por_cobrar: str = "1104"
    cuenta_comision: str = "4302"
    cuenta_ingreso_juego: str = "5101"
    cuenta_ingreso_dlc: str = "5102"
    cuenta_bancos: str = "1103"
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
    cuentas_afectadas: tuple = ()


@dataclass(frozen=True)
class VistaPreviaConciliacion:
    eventos: int
    total: Decimal
    cuentas_por_cobrar: Decimal
    comision: Decimal
    cuentas_afectadas: tuple = ()


def _ahora():
    return datetime.now(timezone.utc)


class VentasService:
    ROLES_CONSULTA = frozenset({Rol.CONTADOR_GENERAL, Rol.ADMINISTRADOR})
    ROLES_REGISTRO = frozenset({Rol.CONTADOR_GENERAL, Rol.ADMINISTRADOR})

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
                impuesto=CERO, origen=OrigenVenta.REAL):
        """CU-08.4: valida y guarda un evento; queda pendiente de revisión."""
        referencia = f"Steam {identificador}"[:60]
        try:
            moneda = moneda.upper()
            if moneda != self._config.moneda:
                raise MonedaNoAdmitidaError(
                    f"Moneda {moneda} no admitida; solo se reciben ventas en "
                    f"{self._config.moneda}."
                )
            if origen not in OrigenVenta.values:
                raise EventoInvalidoError("El origen de la venta no es válido.")
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
                impuesto=impuesto, origen=origen,
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
        """CU-08.3: cobro que se registraría (Debe Bancos / Haber 1104)."""
        self._verificar(actor, self.ROLES_REGISTRO)
        ventas = self._ventas_por_cobrar(desde, hasta)
        total, neto, comision = self._importes(ventas)
        return VistaPreviaConciliacion(
            len(ventas), total, neto, comision,
            tuple(self._cuentas_afectadas(neto)),
        )

    def conciliar(self, actor, desde, hasta):
        """CU-08.3: traslada a Bancos el neto por cobrar del período.

        Cada período se concilia una sola vez; un rango que se solape con
        uno ya conciliado se rechaza.
        """
        self._verificar(actor, self.ROLES_REGISTRO)
        try:
            self._ventas_por_cobrar(desde, hasta)
        except VentasError as error:
            self._bitacora.registrar(
                Accion.CONCILIACION_VENTAS, Resultado.RECHAZADO, actor=actor,
                referencia=f"Steam {desde} a {hasta}"[:60],
                detalle=str(error)[:500],
            )
            raise
        with self._transaccion():
            self._repositorio.bloquear_conciliacion()
            ventas = self._ventas_por_cobrar(desde, hasta)
            for venta in ventas:
                self._cobrar(actor, venta)
            total, neto, comision = self._importes(ventas)
            self._repositorio.crear_conciliacion(
                desde=desde, hasta=hasta, ventas=len(ventas), importe=neto,
                usuario=actor,
            )
            self._bitacora.registrar(
                Accion.CONCILIACION_VENTAS, Resultado.EXITOSO, actor=actor,
                referencia=f"Steam {desde} a {hasta}"[:60],
                detalle=(f"Ventas cobradas: {len(ventas)}; "
                         f"Bancos {self._config.cuenta_bancos} / "
                         f"{self._config.cuenta_por_cobrar}: {neto:.2f}"),
            )
            return ResumenConciliacion(
                len(ventas), total, neto, comision, (),
                tuple(self._cuentas_afectadas(neto)),
            )

    def conciliar_cierre(self, actor, desde, hasta):
        """Al cerrar el período: cobra lo que quede por conciliar.

        Lo llama el cierre dentro de su transacción, antes de marcar el
        período como cerrado. Sin ventas por cobrar no hace nada.
        """
        self._verificar(actor, self.ROLES_REGISTRO)
        ventas = [venta for venta in
                  self._repositorio.ventas_en_periodo(desde, hasta)
                  if venta.estado == EstadoVenta.REGISTRADA
                  and not venta.transaccion_cobro_id
                  and self._por_cobrar(venta) > CERO]
        if not ventas:
            return None
        for venta in ventas:
            self._cobrar(actor, venta)
        total, neto, comision = self._importes(ventas)
        self._repositorio.crear_conciliacion(
            desde=desde, hasta=hasta, ventas=len(ventas), importe=neto,
            usuario=actor,
        )
        self._bitacora.registrar(
            Accion.CONCILIACION_VENTAS, Resultado.EXITOSO, actor=actor,
            referencia=f"Cierre {desde} a {hasta}"[:60],
            detalle=(f"Conciliación al cierre. Ventas cobradas: "
                     f"{len(ventas)}; Bancos {self._config.cuenta_bancos} / "
                     f"{self._config.cuenta_por_cobrar}: {neto:.2f}"),
        )
        return ResumenConciliacion(
            len(ventas), total, neto, comision, (),
            tuple(self._cuentas_afectadas(neto)),
        )

    def _ventas_por_cobrar(self, desde, hasta):
        if desde > hasta:
            raise RangoConciliacionInvalidoError()
        previa = self._repositorio.conciliacion_que_se_solapa(desde, hasta)
        if previa is not None:
            raise PeriodoYaConciliadoError(
                f"El período del {previa.desde:%d/%m/%Y} al "
                f"{previa.hasta:%d/%m/%Y} ya fue conciliado; no se puede "
                "volver a conciliar."
            )
        ventas = self._repositorio.ventas_en_periodo(desde, hasta)
        pendientes = sum(1 for venta in ventas
                         if venta.estado != EstadoVenta.REGISTRADA)
        if pendientes:
            raise ConciliacionNoPermitidaError(
                f"Hay {pendientes} venta(s) sin contabilizar en el período; "
                "contabilízalas antes de conciliar."
            )
        por_cobrar = [venta for venta in ventas
                      if not venta.transaccion_cobro_id
                      and self._por_cobrar(venta) > CERO]
        if not por_cobrar:
            raise ConciliacionNoPermitidaError(
                "No hay ventas contabilizadas por cobrar en el período."
            )
        try:
            cerrado = any(self._mayor.periodo_de(venta.fecha).cerrado
                          for venta in por_cobrar)
        except LibroMayorError as exc:
            raise ConciliacionNoPermitidaError(str(exc)) from exc
        if cerrado:
            raise ConciliacionNoPermitidaError(
                "El período contable está cerrado; no admite el cobro."
            )
        return por_cobrar

    def _por_cobrar(self, venta):
        """Lo que la venta cargó a la cuenta por cobrar en su asiento."""
        return self._repositorio.importe_por_cobrar(
            venta, self._config.cuenta_por_cobrar
        )

    def _importes(self, ventas):
        total = sum((venta.total for venta in ventas), CERO)
        comision = sum((venta.comision for venta in ventas), CERO)
        neto = sum((self._por_cobrar(venta) for venta in ventas), CERO)
        return total, neto, comision

    def _cobrar(self, actor, venta):
        """Debe Bancos / Haber Cuentas por cobrar a plataformas.

        Cobra lo que la venta cargó a la cuenta por cobrar, así 1104 queda
        saldada aunque la venta se haya asentado con un esquema anterior.
        """
        if venta.transaccion_cobro_id:
            return
        importe_cobro = self._por_cobrar(venta)
        try:
            transaccion = self._mayor.crear_transaccion(usuario=actor)
            for codigo, importe in (
                    (self._config.cuenta_bancos, importe_cobro),
                    (self._config.cuenta_por_cobrar, -importe_cobro)):
                self._mayor.crear_movimiento(
                    transaccion=transaccion, cuenta=self._cuenta(codigo),
                    fecha=venta.fecha,
                    concepto=(f"Cobro conciliado Steam "
                              f"{venta.identificador}")[:200],
                    referencia=f"COBRO {venta.identificador}"[:40],
                    tipo=TipoMovimiento.COMPROBANTE_INGRESO,
                    importe=importe,
                )
        except LibroMayorError as exc:
            raise ContabilizacionError(str(exc)) from exc
        self._repositorio.marcar_cobrada(venta, transaccion)

    def _cuentas_afectadas(self, neto):
        filas = []
        for codigo, debe, haber in (
                (self._config.cuenta_bancos, neto, CERO),
                (self._config.cuenta_por_cobrar, CERO, neto)):
            try:
                cuenta = self._mayor.obtener_cuenta(codigo)
                denominacion = getattr(cuenta, "denominacion", codigo)
            except (AttributeError, LibroMayorError):
                denominacion = codigo
            filas.append({"codigo": codigo, "denominacion": denominacion,
                          "debe": debe, "haber": haber})
        return filas

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
