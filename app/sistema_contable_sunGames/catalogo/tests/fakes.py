from catalogo.exceptions import (
    CuentaNoEncontradaError,
    GrupoInvalidoError,
    GuardadoCuentaError,
    NaturalezaInvalidaError,
    RubroInvalidoError,
)
from catalogo.models import Cuenta, Naturaleza, Rubro
from catalogo.services import normalizar_denominacion

ACTIVO = Rubro(codigo="1", nombre="Activo")
PASIVO = Rubro(codigo="2", nombre="Pasivo")
DEUDORA = Naturaleza(codigo="1", nombre="Deudora")
ACREEDORA = Naturaleza(codigo="2", nombre="Acreedora")


def crear_cuenta(codigo, denominacion, rubro=ACTIVO, naturaleza=DEUDORA,
                 activa=True):
    return Cuenta(
        codigo=codigo, denominacion=denominacion,
        denominacion_normalizada=normalizar_denominacion(denominacion),
        rubro=rubro, naturaleza=naturaleza, activa=activa,
        descripcion="Descripción", reglas_uso="Reglas",
    )


class CuentaRepositoryEnMemoria:
    def __init__(self, cuentas=(), grupos=((ACTIVO, DEUDORA),)):
        self.cuentas = {cuenta.codigo: cuenta for cuenta in cuentas}
        self._rubros = {r.codigo: r for r in (ACTIVO, PASIVO)}
        self._naturalezas = {n.codigo: n for n in (DEUDORA, ACREEDORA)}
        self._grupos = {(r.codigo, n.codigo) for r, n in grupos}
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

    def existe_grupo(self, rubro, naturaleza):
        return (rubro.codigo, naturaleza.codigo) in self._grupos

    def bloquear_grupo(self, rubro, naturaleza):
        if not self.existe_grupo(rubro, naturaleza):
            raise GrupoInvalidoError()

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
