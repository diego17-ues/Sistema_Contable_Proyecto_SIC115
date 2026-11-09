"""CU-05 Libro Mayor y CU-05.1 Consultar Saldo de Cuentas.

Captura: cada movimiento se registra sobre la cuenta seleccionada con un
monto en Debe o en Haber (uno de los dos). Se guarda como importe firmado:
Debe es positivo (cargo) y Haber es negativo (abono).

Cuadre: el sistema no exige que los movimientos de un envío sumen cero. El
Contador General es responsable de registrar completas sus transacciones y
lo verifica en el Balance de comprobación, que no se bloquea por diferencia.

Saldo: suma de los importes firmados de la cuenta hasta la fecha de corte.
La naturaleza solo afecta la presentación.
"""

import unicodedata
from contextlib import nullcontext
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from bitacora.eventos import Accion, Resultado
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from .exceptions import (
    CampoObligatorioError,
    ConceptoInvalidoError,
    CuentaNoRegistrableError,
    FechaInvalidaError,
    MovimientoInvalidoError,
    PeriodoCerradoError,
)
from .models import (
    CONCEPTO_MAX_LENGTH,
    REFERENCIA_MAX_LENGTH,
    TipoMovimiento,
)

CERO = Decimal("0.00")
CENTAVO = Decimal("0.01")
IMPORTE_MAXIMO_COLUMNA = Decimal("999999999999.99")
# Código de naturaleza acreedora cargado en catalogo/0004_catalogo_inicial.
NATURALEZA_ACREEDORA = "A"


@dataclass(frozen=True)
class ConfiguracionLibroMayor:
    max_movimientos: int = 20
    # TODO(CU-05): límite de importe no definido; se usa el de la columna.
    importe_maximo: Decimal = None
    concepto_min: int = 3
    concepto_max: int = CONCEPTO_MAX_LENGTH


def sentido(saldo):
    if saldo > 0:
        return "Deudor"
    if saldo < 0:
        return "Acreedor"
    return "Saldado"


@dataclass(frozen=True)
class LineaMayor:
    movimiento: object
    saldo: Decimal

    @property
    def debe(self):
        return self.movimiento.importe if self.movimiento.importe > 0 else None

    @property
    def haber(self):
        importe = self.movimiento.importe
        return -importe if importe < 0 else None

    @property
    def saldo_absoluto(self):
        return abs(self.saldo)

    @property
    def sentido(self):
        return sentido(self.saldo)

    @property
    def correlativo(self):
        movimiento = self.movimiento
        return (
            f"{movimiento.get_tipo_display()}-{movimiento.fecha.year}-"
            f"{movimiento.numero:05d}"
        )


@dataclass(frozen=True)
class ConsultaMayor:
    cuenta: object
    desde: object
    hasta: object
    saldo_inicial: Decimal
    lineas: tuple

    @property
    def saldo_final(self):
        return self.lineas[-1].saldo if self.lineas else self.saldo_inicial


@dataclass(frozen=True)
class SaldoCuenta:
    cuenta: object
    fecha_corte: object
    cargos: Decimal
    abonos: Decimal

    @property
    def saldo(self):
        return self.cargos + self.abonos

    @property
    def sentido(self):
        return sentido(self.saldo)

    @property
    def saldo_absoluto(self):
        return abs(self.saldo)

    @property
    def saldo_presentado(self):
        """Saldo leído según la naturaleza de la cuenta."""
        if self.cuenta.naturaleza.codigo == NATURALEZA_ACREEDORA:
            return -self.saldo
        return self.saldo


@dataclass(frozen=True)
class FilaBalance:
    cuenta: object
    saldo: Decimal

    @property
    def debe(self):
        return self.saldo if self.saldo > 0 else CERO

    @property
    def haber(self):
        return -self.saldo if self.saldo < 0 else CERO


@dataclass(frozen=True)
class BalanceComprobacion:
    fecha_corte: object
    filas: tuple

    @property
    def total_debe(self):
        return sum((fila.debe for fila in self.filas), CERO)

    @property
    def total_haber(self):
        return sum((fila.haber for fila in self.filas), CERO)

    @property
    def diferencia(self):
        return self.total_debe - self.total_haber

    @property
    def balanceado(self):
        return self.diferencia == 0


class LibroMayorService:
    ROLES_REGISTRO = frozenset({Rol.CONTADOR_GENERAL})
    ROLES_CONSULTA = frozenset({Rol.CONTADOR_GENERAL, Rol.ADMINISTRADOR})

    def __init__(self, repositorio, bitacora, configuracion=None,
                 transaccion=nullcontext):
        self._repositorio = repositorio
        self._bitacora = bitacora
        self._config = configuracion or ConfiguracionLibroMayor()
        self._transaccion = transaccion

    def puede_registrar(self, actor):
        return actor.activo and actor.rol in self.ROLES_REGISTRO

    def verificar_registro(self, actor):
        self._verificar(actor, self.ROLES_REGISTRO)

    def cuentas(self, actor):
        self._verificar(actor, self.ROLES_CONSULTA)
        return list(self._repositorio.cuentas())

    def registrar(self, actor, *, cuenta, movimientos):
        """Guarda en la cuenta todos los movimientos del envío, o ninguno."""
        self.verificar_registro(actor)
        cuenta = self._cuenta_registrable(self._codigo(cuenta))
        lineas = self._validar_movimientos(movimientos)
        with self._transaccion():
            transaccion = self._repositorio.crear_transaccion(usuario=actor)
            for linea in lineas:
                self._repositorio.crear_movimiento(
                    transaccion=transaccion, cuenta=cuenta, **linea
                )
            self._bitacora.registrar(
                Accion.REGISTRO_TRANSACCION, Resultado.EXITOSO, actor=actor,
                referencia=(
                    f"Transacción {transaccion.pk} · cuenta {cuenta.codigo} "
                    f"· {len(lineas)} movimiento(s)"
                ),
            )
        return transaccion

    def consultar(self, actor, codigo, *, desde=None, hasta=None):
        """Movimientos de la cuenta en el rango, con saldo acumulado."""
        self._verificar(actor, self.ROLES_CONSULTA)
        if desde and hasta and desde > hasta:
            raise FechaInvalidaError(
                "La fecha inicial es posterior a la final.", campo="desde"
            )
        cuenta = self._repositorio.obtener_cuenta(codigo)
        saldo_inicial = CERO
        if desde:
            saldo_inicial = self._suma(
                self._repositorio.totales(cuenta, antes_de=desde)
            )
        saldo = saldo_inicial
        lineas = []
        for movimiento in self._repositorio.movimientos(
            cuenta, desde=desde, hasta=hasta
        ):
            saldo += movimiento.importe
            lineas.append(LineaMayor(movimiento, saldo))
        return ConsultaMayor(
            cuenta, desde, hasta, saldo_inicial, tuple(lineas)
        )

    def saldo(self, actor, codigo, fecha_corte):
        """CU-05.1: saldo acumulado a la fecha de corte."""
        self._verificar(actor, self.ROLES_CONSULTA)
        if fecha_corte is None:
            raise CampoObligatorioError(campo="fecha_corte")
        cuenta = self._repositorio.obtener_cuenta(codigo)
        totales = self._repositorio.totales(cuenta, hasta=fecha_corte)
        return SaldoCuenta(
            cuenta, fecha_corte,
            totales["cargos"] or CERO, totales["abonos"] or CERO,
        )

    def balance_comprobacion(self, actor, fecha_corte):
        """Saldos a la fecha de corte de las cuentas con movimientos."""
        self._verificar(actor, self.ROLES_CONSULTA)
        if fecha_corte is None:
            raise CampoObligatorioError(campo="corte")
        filas = tuple(
            FilaBalance(cuenta, cuenta.saldo)
            for cuenta in self._repositorio.saldos_por_cuenta(
                hasta=fecha_corte
            )
        )
        return BalanceComprobacion(fecha_corte, filas)

    def _validar_movimientos(self, movimientos):
        movimientos = list(movimientos)
        if not movimientos:
            raise MovimientoInvalidoError(
                "Registra al menos un movimiento."
            )
        if len(movimientos) > self._config.max_movimientos:
            raise MovimientoInvalidoError(
                "Se admiten como máximo "
                f"{self._config.max_movimientos} movimientos por registro."
            )
        return [
            self._validar_linea(datos, linea)
            for linea, datos in enumerate(movimientos)
        ]

    def _validar_linea(self, datos, linea):
        return {
            "fecha": self._validar_fecha(datos.get("fecha"), linea),
            "concepto": self._validar_concepto(datos.get("concepto"), linea),
            "referencia": self._validar_referencia(
                datos.get("referencia"), linea
            ),
            "tipo": self._validar_tipo(datos.get("tipo"), linea),
            "importe": self._importe_firmado(
                datos.get("debe"), datos.get("haber"), linea
            ),
        }

    def _validar_fecha(self, fecha, linea):
        if fecha is None:
            raise CampoObligatorioError(campo="fecha", linea=linea)
        try:
            periodo = self._repositorio.periodo_de(fecha)
        except FechaInvalidaError as exc:
            raise FechaInvalidaError(campo="fecha", linea=linea) from exc
        if periodo.cerrado:
            raise PeriodoCerradoError(campo="fecha", linea=linea)
        return fecha

    def _validar_concepto(self, concepto, linea):
        concepto = (concepto or "").strip()
        if not concepto:
            raise CampoObligatorioError(campo="concepto", linea=linea)
        self._rechazar_control(concepto, "concepto", linea)
        if not self._config.concepto_min <= len(concepto) <= (
            self._config.concepto_max
        ):
            raise ConceptoInvalidoError(
                f"La descripción debe tener entre "
                f"{self._config.concepto_min} y {self._config.concepto_max} "
                "caracteres.", campo="concepto", linea=linea,
            )
        return concepto

    def _validar_referencia(self, referencia, linea):
        referencia = (referencia or "").strip()
        self._rechazar_control(referencia, "referencia", linea)
        if len(referencia) > REFERENCIA_MAX_LENGTH:
            raise MovimientoInvalidoError(
                "La referencia admite como máximo "
                f"{REFERENCIA_MAX_LENGTH} caracteres.",
                campo="referencia", linea=linea,
            )
        return referencia

    @staticmethod
    def _rechazar_control(texto, campo, linea):
        if any(unicodedata.category(c) == "Cc" for c in texto):
            raise ConceptoInvalidoError(
                "El texto contiene caracteres de control.",
                campo=campo, linea=linea,
            )

    @staticmethod
    def _validar_tipo(tipo, linea):
        tipo = (tipo or "").strip()
        if not tipo:
            raise CampoObligatorioError(campo="tipo", linea=linea)
        if tipo not in TipoMovimiento.values:
            raise MovimientoInvalidoError(
                "El tipo de transacción no es válido.",
                campo="tipo", linea=linea,
            )
        return tipo

    def _importe_firmado(self, debe, haber, linea):
        """Debe se guarda positivo y Haber negativo; solo uno por línea."""
        debe, haber = self._vacio_a_none(debe), self._vacio_a_none(haber)
        if debe is None and haber is None:
            raise CampoObligatorioError(
                "Registra un monto en Debe o en Haber.",
                campo="debe", linea=linea,
            )
        if debe is not None and haber is not None:
            raise MovimientoInvalidoError(
                "Registra el monto solo en Debe o solo en Haber.",
                campo="haber", linea=linea,
            )
        if debe is not None:
            return self._importe(debe, linea, "debe")
        return -self._importe(haber, linea, "haber")

    @staticmethod
    def _vacio_a_none(valor):
        if isinstance(valor, str):
            valor = valor.strip()
        return None if valor is None or valor == "" else valor

    def _importe(self, valor, linea, campo):
        if not isinstance(valor, (Decimal, str, int)) or isinstance(
            valor, bool
        ):
            raise MovimientoInvalidoError(
                "El monto debe ser un número decimal.",
                campo=campo, linea=linea,
            )
        try:
            importe = Decimal(valor)
        except InvalidOperation as exc:
            raise MovimientoInvalidoError(
                "El monto no es un número válido.",
                campo=campo, linea=linea,
            ) from exc
        if not importe.is_finite():
            raise MovimientoInvalidoError(
                "El monto no es un número válido.",
                campo=campo, linea=linea,
            )
        if importe != importe.quantize(CENTAVO):
            raise MovimientoInvalidoError(
                "El monto admite como máximo dos decimales.",
                campo=campo, linea=linea,
            )
        if importe <= 0:
            raise MovimientoInvalidoError(
                "El monto debe ser mayor que cero.",
                campo=campo, linea=linea,
            )
        maximo = self._config.importe_maximo or IMPORTE_MAXIMO_COLUMNA
        if importe > maximo:
            raise MovimientoInvalidoError(
                f"El monto supera el máximo permitido ({maximo:,.2f}).",
                campo=campo, linea=linea,
            )
        return importe.quantize(CENTAVO)

    @staticmethod
    def _codigo(valor):
        codigo = str(valor or "").strip()
        if not codigo:
            raise CampoObligatorioError(campo="cuenta")
        return codigo

    def _cuenta_registrable(self, codigo):
        try:
            cuenta = self._repositorio.obtener_cuenta(codigo)
        except CuentaNoRegistrableError as exc:
            raise CuentaNoRegistrableError(str(exc), campo="cuenta") from exc
        if not cuenta.activa:
            raise CuentaNoRegistrableError(
                "La cuenta está dada de baja.", campo="cuenta"
            )
        if self._repositorio.tiene_subcuentas(cuenta):
            raise CuentaNoRegistrableError(
                "La cuenta tiene subcuentas; solo se registran cuentas de "
                "detalle.", campo="cuenta",
            )
        return cuenta

    @staticmethod
    def _suma(totales):
        return (totales["cargos"] or CERO) + (totales["abonos"] or CERO)

    @staticmethod
    def _verificar(actor, roles):
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol not in roles:
            raise RolNoAutorizadoError()
