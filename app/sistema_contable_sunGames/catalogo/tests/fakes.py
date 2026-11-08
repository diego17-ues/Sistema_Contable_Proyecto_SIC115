from catalogo.exceptions import (
    CuentaNoEncontradaError,
    GuardadoCuentaError,
    NaturalezaInvalidaError,
    RubroInvalidoError,
    SubtipoInvalidoError,
)
from catalogo.models import Cuenta, Naturaleza, Rubro, Subtipo
from catalogo.services import normalizar_denominacion

ACTIVO = Rubro(codigo="1", nombre="Activo")
PASIVO = Rubro(codigo="2", nombre="Pasivo")
CORRIENTE = Subtipo(rubro=ACTIVO, codigo="1", nombre="Activo corriente")
NO_CORRIENTE = Subtipo(rubro=ACTIVO, codigo="2", nombre="Activo no corriente")
PASIVO_CORRIENTE = Subtipo(rubro=PASIVO, codigo="1", nombre="Pasivo corriente")
DEUDORA = Naturaleza(codigo="D", nombre="Deudora")
ACREEDORA = Naturaleza(codigo="A", nombre="Acreedora")


def crear_cuenta(codigo, denominacion, subtipo=CORRIENTE,
                 naturaleza=DEUDORA, activa=True):
    return Cuenta(
        codigo=codigo, denominacion=denominacion,
        denominacion_normalizada=normalizar_denominacion(denominacion),
        rubro=subtipo.rubro, subtipo=subtipo, naturaleza=naturaleza,
        activa=activa,
    )


class CuentaRepositoryEnMemoria:
    def __init__(self, cuentas=()):
        self.cuentas = {cuenta.codigo: cuenta for cuenta in cuentas}
        self._rubros = {r.codigo: r for r in (ACTIVO, PASIVO)}
        self._subtipos = {
            s.prefijo: s for s in (CORRIENTE, NO_CORRIENTE, PASIVO_CORRIENTE)
        }
        self._naturalezas = {n.codigo: n for n in (DEUDORA, ACREEDORA)}
        self.aprobaciones = []
        self.falla_al_guardar = False

    def listar(self, *, codigo="", denominacion="", rubro="", naturaleza="",
               activa=None):
        return [
            c for c in sorted(self.cuentas.values(), key=lambda c: c.codigo)
            if c.codigo.startswith(codigo)
            and denominacion.lower() in c.denominacion.lower()
            and (not rubro or c.rubro.codigo == rubro)
            and (not naturaleza or c.naturaleza.codigo == naturaleza)
            and (activa is None or c.activa == activa)
        ]

    def obtener_por_codigo(self, codigo):
        try:
            return self.cuentas[codigo]
        except KeyError as exc:
            raise CuentaNoEncontradaError() from exc

    def existe_denominacion(self, normalizada, *, excluir_codigo=None):
        return any(
            c.denominacion_normalizada == normalizada
            for c in self.cuentas.values() if c.codigo != excluir_codigo
        )

    def rubros(self):
        return list(self._rubros.values())

    def subtipos(self):
        return list(self._subtipos.values())

    def naturalezas(self):
        return list(self._naturalezas.values())

    def obtener_rubro(self, codigo):
        try:
            return self._rubros[codigo]
        except KeyError as exc:
            raise RubroInvalidoError() from exc

    def obtener_naturaleza(self, codigo):
        try:
            return self._naturalezas[codigo]
        except KeyError as exc:
            raise NaturalezaInvalidaError() from exc

    def obtener_subtipo(self, rubro, codigo):
        try:
            return self._subtipos[rubro.codigo + codigo]
        except KeyError as exc:
            raise SubtipoInvalidoError() from exc

    def bloquear_subtipo(self, subtipo):
        return subtipo

    def codigos_con_prefijo(self, prefijo):
        return [c for c in self.cuentas if c.startswith(prefijo)]

    def nueva(self, **campos):
        return Cuenta(**campos)

    def guardar(self, cuenta):
        if self.falla_al_guardar:
            raise GuardadoCuentaError()
        self.cuentas[cuenta.codigo] = cuenta
        return cuenta

    def registrar_aprobacion(self, cuenta, *, tipo, usuario, documentacion,
                             cambios=()):
        self.aprobaciones.append({
            "cuenta": cuenta.codigo, "tipo": tipo, "usuario": usuario,
            "documentacion": documentacion, "cambios": list(cambios),
        })


class BitacoraEnMemoria:
    def __init__(self):
        self.registros = []

    def registrar(self, accion, resultado, *, actor=None, afectado=None,
                  referencia=""):
        self.registros.append({
            "accion": accion, "resultado": resultado, "actor": actor,
            "referencia": referencia,
        })
