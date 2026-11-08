"""CU-05 Libro Mayor y CU-05.1 Consultar Saldo de Cuentas.

Convención de signo: un importe positivo carga (debita) la cuenta y uno
negativo la abona (acredita). No hay columnas de debe ni haber.

Saldo: suma de los importes firmados de la cuenta hasta la fecha de corte.
La naturaleza solo afecta la presentación: una cuenta acreedora muestra su
saldo con el signo invertido, de modo que su saldo normal se lee positivo.
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
    CuentaRepetidaError,
    FechaInvalidaError,
    MovimientoInvalidoError,
    PeriodoCerradoError,
    TransaccionDescuadradaError,
)
from .models import CONCEPTO_MAX_LENGTH

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


@dataclass(frozen=True)
class LineaMayor:
    movimiento: object
    saldo: Decimal


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
        if self.saldo > 0:
            return "Deudor"
        if self.saldo < 0:
            return "Acreedor"
        return "Saldado"

    @property
    def saldo_presentado(self):
        """Saldo leído según la naturaleza de la cuenta."""
        if self.cuenta.naturaleza.codigo == NATURALEZA_ACREEDORA:
            return -self.saldo
        return self.saldo


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

    def registrar(self, actor, *, fecha, concepto, movimientos):
        """Guarda la transacción y todos sus movimientos, o nada."""
        self.verificar_registro(actor)
        self._validar_fecha(fecha)
        concepto = self._validar_concepto(concepto)
        lineas = self._validar_movimientos(movimientos)
        with self._transaccion():
            transaccion = self._repositorio.crear_transaccion(
                fecha=fecha, concepto=concepto, usuario=actor
            )
            for cuenta, importe in lineas:
                self._repositorio.crear_movimiento(
                    transaccion=transaccion, cuenta=cuenta, importe=importe
                )
            self._bitacora.registrar(
                Accion.REGISTRO_TRANSACCION, Resultado.EXITOSO, actor=actor,
                referencia=f"Transacción {transaccion.pk}",
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

    def _validar_fecha(self, fecha):
        if fecha is None:
            raise CampoObligatorioError(campo="fecha")
        periodo = self._repositorio.periodo_de(fecha)
        if periodo.cerrado:
            raise PeriodoCerradoError(campo="fecha")

    def _validar_concepto(self, concepto):
        concepto = (concepto or "").strip()
        if not concepto:
            raise CampoObligatorioError(campo="concepto")
        if any(unicodedata.category(c) == "Cc" for c in concepto):
            raise ConceptoInvalidoError(
                "El concepto contiene caracteres de control.",
                campo="concepto",
            )
        if not self._config.concepto_min <= len(concepto) <= (
            self._config.concepto_max
        ):
            raise ConceptoInvalidoError(
                f"El concepto debe tener entre {self._config.concepto_min} "
                f"y {self._config.concepto_max} caracteres.",
                campo="concepto",
            )
        return concepto

    def _validar_movimientos(self, movimientos):
        movimientos = list(movimientos)
        if len(movimientos) < 2:
            raise MovimientoInvalidoError(
                "La transacción requiere al menos dos movimientos."
            )
        if len(movimientos) > self._config.max_movimientos:
            raise MovimientoInvalidoError(
                "La transacción admite como máximo "
                f"{self._config.max_movimientos} movimientos."
            )
        codigos = [
            self._codigo(m.get("cuenta"), linea)
            for linea, m in enumerate(movimientos)
        ]
        importes = [
            self._importe(m.get("importe"), linea)
            for linea, m in enumerate(movimientos)
        ]
        self._rechazar_repetidas(codigos)
        cuentas = [
            self._cuenta_registrable(codigo, linea)
            for linea, codigo in enumerate(codigos)
        ]
        diferencia = sum(importes, CERO)
        if diferencia != 0:
            raise TransaccionDescuadradaError(diferencia)
        return list(zip(cuentas, importes))

    @staticmethod
    def _codigo(valor, linea):
        codigo = str(valor or "").strip()
        if not codigo:
            raise CampoObligatorioError(campo="cuenta", linea=linea)
        return codigo

    def _importe(self, valor, linea):
        if isinstance(valor, str):
            valor = valor.strip()
        if valor is None or valor == "":
            raise CampoObligatorioError(campo="importe", linea=linea)
        if not isinstance(valor, (Decimal, str, int)) or isinstance(
            valor, bool
        ):
            raise MovimientoInvalidoError(
                "El importe debe ser un número decimal.",
                campo="importe", linea=linea,
            )
        try:
            importe = Decimal(valor)
        except InvalidOperation as exc:
            raise MovimientoInvalidoError(
                "El importe no es un número válido.",
                campo="importe", linea=linea,
            ) from exc
        if not importe.is_finite():
            raise MovimientoInvalidoError(
                "El importe no es un número válido.",
                campo="importe", linea=linea,
            )
        if importe != importe.quantize(CENTAVO):
            raise MovimientoInvalidoError(
                "El importe admite como máximo dos decimales.",
                campo="importe", linea=linea,
            )
        if importe == 0:
            raise MovimientoInvalidoError(
                "El importe debe ser distinto de cero.",
                campo="importe", linea=linea,
            )
        maximo = self._config.importe_maximo or IMPORTE_MAXIMO_COLUMNA
        if abs(importe) > maximo:
            raise MovimientoInvalidoError(
                f"El importe supera el máximo permitido ({maximo:,.2f}).",
                campo="importe", linea=linea,
            )
        return importe.quantize(CENTAVO)

    @staticmethod
    def _rechazar_repetidas(codigos):
        repetidas = [
            linea for linea, codigo in enumerate(codigos)
            if codigos.count(codigo) > 1
        ]
        if repetidas:
            raise CuentaRepetidaError(campo="cuenta", lineas=repetidas)

    def _cuenta_registrable(self, codigo, linea):
        try:
            cuenta = self._repositorio.obtener_cuenta(codigo)
        except CuentaNoRegistrableError as exc:
            raise CuentaNoRegistrableError(
                str(exc), campo="cuenta", linea=linea
            ) from exc
        if not cuenta.activa:
            raise CuentaNoRegistrableError(
                "La cuenta está dada de baja.", campo="cuenta", linea=linea
            )
        if self._repositorio.tiene_subcuentas(cuenta):
            raise CuentaNoRegistrableError(
                "La cuenta tiene subcuentas; solo se registran cuentas de "
                "detalle.", campo="cuenta", linea=linea,
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
