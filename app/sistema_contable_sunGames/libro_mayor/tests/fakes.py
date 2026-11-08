from contextlib import contextmanager

from catalogo.models import Cuenta, Naturaleza
from libro_mayor.exceptions import (
    CuentaNoRegistrableError,
    FechaInvalidaError,
    GuardadoTransaccionError,
)
from libro_mayor.models import Movimiento, PeriodoContable, Transaccion

DEUDORA = Naturaleza(codigo="D", nombre="Deudora")
ACREEDORA = Naturaleza(codigo="A", nombre="Acreedora")


def cuenta(codigo, naturaleza=DEUDORA, activa=True):
    return Cuenta(
        codigo=codigo, denominacion=f"Cuenta {codigo}",
        naturaleza=naturaleza, activa=activa,
    )


class TransaccionRepositoryEnMemoria:
    def __init__(self, cuentas=(), periodos=(), con_subcuentas=()):
        self._cuentas = {c.codigo: c for c in cuentas}
        self._periodos = list(periodos)
        self._con_subcuentas = set(con_subcuentas)
        self.transacciones = []
        self.guardados = []
        self.fallar_en_movimiento = None

    @contextmanager
    def transaccion_simulada(self):
        respaldo = (list(self.transacciones), list(self.guardados))
        try:
            yield
        except Exception:
            self.transacciones, self.guardados = respaldo
            raise

    def periodo_de(self, fecha):
        for periodo in self._periodos:
            if periodo.fecha_inicio <= fecha <= periodo.fecha_fin:
                return periodo
        raise FechaInvalidaError(campo="fecha")

    def cuentas(self):
        return list(self._cuentas.values())

    def obtener_cuenta(self, codigo):
        try:
            return self._cuentas[codigo]
        except KeyError as exc:
            raise CuentaNoRegistrableError("La cuenta no existe.") from exc

    def tiene_subcuentas(self, cuenta):
        return cuenta.codigo in self._con_subcuentas

    def crear_transaccion(self, *, fecha, concepto, usuario):
        transaccion = Transaccion(
            pk=len(self.transacciones) + 1, fecha=fecha, concepto=concepto,
            usuario=usuario,
        )
        self.transacciones.append(transaccion)
        return transaccion

    def crear_movimiento(self, *, transaccion, cuenta, importe):
        if len(self.guardados) + 1 == self.fallar_en_movimiento:
            raise GuardadoTransaccionError()
        movimiento = Movimiento(
            transaccion=transaccion, cuenta=cuenta, importe=importe
        )
        self.guardados.append(movimiento)
        return movimiento

    def movimientos_de(self, cuenta):
        return [m for m in self.guardados if m.cuenta is cuenta]

    def movimientos(self, cuenta, *, desde=None, hasta=None):
        return [
            m for m in self.movimientos_de(cuenta)
            if (not desde or m.transaccion.fecha >= desde)
            and (not hasta or m.transaccion.fecha <= hasta)
        ]

    def totales(self, cuenta, *, hasta=None, antes_de=None):
        importes = [
            m.importe for m in self.movimientos_de(cuenta)
            if (not hasta or m.transaccion.fecha <= hasta)
            and (not antes_de or m.transaccion.fecha < antes_de)
        ]
        cargos = [i for i in importes if i > 0]
        abonos = [i for i in importes if i < 0]
        return {
            "cargos": sum(cargos) if cargos else None,
            "abonos": sum(abonos) if abonos else None,
        }


def periodo(inicio, fin, cerrado=False):
    return PeriodoContable(
        nombre="P", fecha_inicio=inicio, fecha_fin=fin, cerrado=cerrado
    )
