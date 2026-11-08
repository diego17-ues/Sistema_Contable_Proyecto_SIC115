"""Casos de uso de CU-06 Catálogo de Cuentas."""

import unicodedata
from contextlib import nullcontext
from copy import copy
from dataclasses import dataclass

from bitacora.eventos import Accion, Resultado
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from .exceptions import (
    CodigoInmodificableError,
    CodigoNoAsignableError,
    CuentaDuplicadaError,
    DocumentacionIncompletaError,
    GrupoInvalidoError,
    SinCambiosError,
    SubcuentaNoPermitidaError,
)
from .models import AprobacionCuenta

ULTIMO_NUMERO_DEL_GRUPO = 99
CAMPOS_DOCUMENTACION = {
    "justificacion": "Falta la justificación.",
    "referencia_respaldo": "Falta la referencia de respaldo.",
    "acuerdo_numero": "Falta el número del acuerdo de Junta Directiva.",
    "acuerdo_fecha": "Falta la fecha del acuerdo de Junta Directiva.",
}
ETIQUETAS_MODIFICABLES = {
    "denominacion": "Denominación",
    "rubro": "Rubro",
    "naturaleza": "Naturaleza",
    "descripcion": "Descripción",
    "reglas_uso": "Reglas de uso",
}
CAMPOS_DE_SUBCUENTA = ("cuenta_padre", "codigo_padre", "subcuenta")


@dataclass(frozen=True)
class Cambio:
    campo: str
    etiqueta: str
    anterior: str
    nuevo: str


@dataclass(frozen=True)
class Revision:
    """Datos propuestos de una modificación, antes de guardarla."""

    cuenta: object
    propuesta: object
    cambios: tuple

    @property
    def conserva_codigo(self):
        """Cambió el rubro o la naturaleza, pero el código se conserva."""
        return any(c.campo in ("rubro", "naturaleza") for c in self.cambios)


def normalizar_denominacion(texto):
    """Clave para detectar denominaciones equivalentes."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(
        c for c in descompuesto if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.casefold().split())


class CatalogoCuentasService:
    """CU-06: consulta, registro (CU-06.1) y modificación (CU-06.3)."""

    ROLES_CONSULTA = frozenset({Rol.ADMINISTRADOR, Rol.CONTADOR_GENERAL})
    ROLES_ESCRITURA = frozenset({Rol.ADMINISTRADOR})

    def __init__(self, repositorio, bitacora, transaccion=nullcontext):
        self._repositorio = repositorio
        self._bitacora = bitacora
        self._transaccion = transaccion

    def opciones(self, actor):
        """Rubros y naturalezas de la fuente configurable."""
        self._verificar(actor, self.ROLES_CONSULTA)
        return {
            "rubros": list(self._repositorio.rubros()),
            "naturalezas": list(self._repositorio.naturalezas()),
        }

    def listar(self, actor, **filtros):
        self._verificar(actor, self.ROLES_CONSULTA)
        return self._repositorio.listar(**filtros)

    def obtener(self, actor, codigo):
        self._verificar(actor, self.ROLES_CONSULTA)
        return self._repositorio.obtener_por_codigo(codigo)

    def puede_modificar(self, actor):
        return actor.activo and actor.rol in self.ROLES_ESCRITURA

    def verificar_escritura(self, actor):
        self._verificar(actor, self.ROLES_ESCRITURA)

    def registrar(self, actor, datos):
        """CU-06.1: alta con el siguiente código libre del grupo."""
        self.verificar_escritura(actor)
        self._rechazar_campos_no_editables(datos, codigo_actual=None)
        documentacion = self._documentacion(datos)
        rubro, naturaleza = self._clasificacion(datos)
        denominacion = datos["denominacion"].strip()
        normalizada = self._denominacion_disponible(denominacion)
        with self._transaccion():
            self._repositorio.bloquear_grupo(rubro, naturaleza)
            codigo = self._siguiente_codigo(rubro.codigo + naturaleza.codigo)
            cuenta = self._repositorio.nueva(
                codigo=codigo,
                denominacion=denominacion,
                denominacion_normalizada=normalizada,
                rubro=rubro,
                naturaleza=naturaleza,
                descripcion=datos.get("descripcion", ""),
                reglas_uso=datos.get("reglas_uso", ""),
            )
            cuenta = self._repositorio.guardar(cuenta)
            self._repositorio.registrar_aprobacion(
                cuenta, tipo=AprobacionCuenta.Tipo.ALTA, usuario=actor,
                documentacion=documentacion,
            )
            self._registrar(Accion.ALTA_CUENTA, actor, cuenta)
        return cuenta

    def revisar(self, actor, codigo, datos):
        """CU-06.3: valida y presenta los cambios sin guardarlos."""
        self.verificar_escritura(actor)
        cuenta = self._repositorio.obtener_por_codigo(codigo)
        self._rechazar_campos_no_editables(datos, codigo_actual=cuenta.codigo)
        self._documentacion(datos)
        rubro, naturaleza = self._clasificacion(datos)
        denominacion = datos["denominacion"].strip()
        propuesta = copy(cuenta)
        propuesta.denominacion = denominacion
        propuesta.denominacion_normalizada = self._denominacion_disponible(
            denominacion, excluir_codigo=cuenta.codigo
        )
        propuesta.rubro = rubro
        propuesta.naturaleza = naturaleza
        propuesta.descripcion = datos.get("descripcion", "")
        propuesta.reglas_uso = datos.get("reglas_uso", "")
        cambios = tuple(self._cambios(cuenta, propuesta))
        if not cambios:
            raise SinCambiosError()
        return Revision(cuenta=cuenta, propuesta=propuesta, cambios=cambios)

    def modificar(self, actor, codigo, datos):
        """CU-06.3: guarda los cambios conservando el código."""
        revision = self.revisar(actor, codigo, datos)
        with self._transaccion():
            cuenta = self._repositorio.guardar(revision.propuesta)
            self._repositorio.registrar_aprobacion(
                cuenta, tipo=AprobacionCuenta.Tipo.MODIFICACION,
                usuario=actor, documentacion=self._documentacion(datos),
                cambios=revision.cambios,
            )
            self._registrar(Accion.MODIFICACION_CUENTA, actor, cuenta)
        return revision

    def _rechazar_campos_no_editables(self, datos, *, codigo_actual):
        if any(datos.get(campo) for campo in CAMPOS_DE_SUBCUENTA):
            raise SubcuentaNoPermitidaError()
        if "codigo" not in datos or datos["codigo"] == codigo_actual:
            return
        if codigo_actual is None:
            raise CodigoInmodificableError(
                "El código lo asigna el sistema; no se captura."
            )
        raise CodigoInmodificableError()

    @staticmethod
    def _documentacion(datos):
        documentacion = {}
        for campo, mensaje in CAMPOS_DOCUMENTACION.items():
            valor = datos.get(campo)
            if isinstance(valor, str):
                valor = valor.strip()
            if not valor:
                raise DocumentacionIncompletaError(mensaje, campo=campo)
            documentacion[campo] = valor
        return documentacion

    def _clasificacion(self, datos):
        rubro = self._repositorio.obtener_rubro(datos.get("rubro"))
        naturaleza = self._repositorio.obtener_naturaleza(
            datos.get("naturaleza")
        )
        if not self._repositorio.existe_grupo(rubro, naturaleza):
            raise GrupoInvalidoError()
        return rubro, naturaleza

    def _denominacion_disponible(self, denominacion, excluir_codigo=None):
        normalizada = normalizar_denominacion(denominacion)
        if self._repositorio.existe_denominacion(
            normalizada, excluir_codigo=excluir_codigo
        ):
            raise CuentaDuplicadaError()
        return normalizada

    def _siguiente_codigo(self, prefijo):
        """Menor número sin usar; los códigos dados de baja siguen usados."""
        usados = set(self._repositorio.codigos_con_prefijo(prefijo))
        for numero in range(1, ULTIMO_NUMERO_DEL_GRUPO + 1):
            codigo = f"{prefijo}{numero:02d}"
            if codigo not in usados:
                return codigo
        raise CodigoNoAsignableError()

    @staticmethod
    def _cambios(actual, propuesta):
        for campo, etiqueta in ETIQUETAS_MODIFICABLES.items():
            anterior = getattr(actual, campo)
            nuevo = getattr(propuesta, campo)
            clave_anterior = getattr(anterior, "codigo", anterior)
            clave_nueva = getattr(nuevo, "codigo", nuevo)
            if clave_anterior != clave_nueva:
                yield Cambio(campo, etiqueta, str(anterior), str(nuevo))

    def _registrar(self, accion, actor, cuenta):
        self._bitacora.registrar(
            accion, Resultado.EXITOSO, actor=actor,
            referencia=f"Cuenta {cuenta.codigo}",
        )

    @staticmethod
    def _verificar(actor, roles):
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol not in roles:
            raise RolNoAutorizadoError()
