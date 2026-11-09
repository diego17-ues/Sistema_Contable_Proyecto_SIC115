import datetime
from contextlib import contextmanager
from decimal import Decimal

from catalogo.models import Cuenta, Rubro, Subtipo
from estados_financieros.exceptions import (
    GuardadoCierreError,
    PeriodoNoEncontradoError,
)
from estados_financieros.models import EstadoFinancieroEmitido
from libro_mayor.models import EstadoPeriodo, PeriodoContable

SUBTIPOS = {
    "11": "Activo corriente", "12": "Activo no corriente",
    "21": "Pasivo corriente", "22": "Pasivo no corriente",
    "31": "Patrimonio", "41": "Costos de desarrollo",
    "42": "Gastos de administración", "44": "Gastos financieros",
    "45": "Otros egresos", "51": "Ingresos",
}
# Suma cero: Activo 2,200 = Pasivo 700 + Patrimonio 1,000 + utilidad 500.
SALDOS = {
    "1101": "1000", "1103": "500", "1201": "800", "1203": "-100",
    "2101": "-400", "2201": "-300", "3101": "-1000", "5101": "-1500",
    "5103": "100", "4104": "300", "4201": "400", "4401": "50",
    "4503": "150",
}


def cuenta_con_saldo(codigo, saldo):
    rubro = Rubro(codigo=codigo[0], nombre=f"Rubro {codigo[0]}")
    subtipo = Subtipo(rubro=rubro, codigo=codigo[1],
                      nombre=SUBTIPOS[codigo[:2]])
    cuenta = Cuenta(codigo=codigo, denominacion=f"Cuenta {codigo}",
                    rubro=rubro, subtipo=subtipo)
    cuenta.saldo = Decimal(saldo)
    return cuenta


def periodo(pk=1, cerrado=False):
    return PeriodoContable(
        pk=pk, nombre="Ejercicio 2026",
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 12, 31),
        estado=(EstadoPeriodo.CIERRE_PROVISIONAL if cerrado
                else EstadoPeriodo.ABIERTO),
    )


class EstadosRepositoryEnMemoria:
    def __init__(self, periodos=(), saldos=SALDOS, conteo=(3, 13),
                 suma=Decimal("0")):
        self._periodos = {p.pk: p for p in periodos}
        self._saldos = [cuenta_con_saldo(c, s) for c, s in saldos.items()]
        self._saldos.sort(key=lambda c: c.codigo)
        self._conteo = conteo
        self.suma = suma
        self.emitidos = []
        self.fallar_al_cerrar = False
        self.consultas_saldos = 0

    @contextmanager
    def transaccion_simulada(self):
        emitidos = list(self.emitidos)
        estados = {pk: p.estado for pk, p in self._periodos.items()}
        try:
            yield
        except Exception:
            self.emitidos = emitidos
            for pk, estado in estados.items():
                self._periodos[pk].estado = estado
            raise

    def periodos(self):
        return list(self._periodos.values())

    def periodo_mas_reciente(self):
        return (self._periodos[max(self._periodos)]
                if self._periodos else None)

    def obtener_periodo(self, pk):
        try:
            return self._periodos[pk]
        except KeyError as exc:
            raise PeriodoNoEncontradoError() from exc

    def buscar_periodo(self, referencia):
        for p in self._periodos.values():
            if p.nombre == referencia:
                return p
        raise PeriodoNoEncontradoError()

    def saldos(self, *, hasta, desde=None):
        self.consultas_saldos += 1
        return list(self._saldos)

    def conteo(self, periodo):
        return self._conteo

    def suma_balanza(self, *, hasta):
        return self.suma

    def ultimo_emitido(self, periodo, tipo):
        for emitido in reversed(self.emitidos):
            if emitido.periodo is periodo and emitido.tipo == tipo:
                return emitido
        return None

    def guardar_emitido(self, *, periodo, tipo, datos, usuario):
        emitido = EstadoFinancieroEmitido(
            periodo=periodo, tipo=tipo, datos=datos, usuario=usuario,
            fecha_emision=datetime.datetime(2026, 12, 31, 18, 0,
                                            tzinfo=datetime.timezone.utc),
        )
        self.emitidos.append(emitido)
        return emitido

    def cerrar(self, periodo):
        if self.fallar_al_cerrar:
            raise GuardadoCierreError()
        periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL

    def reabrir(self, periodo):
        periodo.estado = EstadoPeriodo.ABIERTO
