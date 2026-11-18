"""Casos de uso del módulo de estimación (subsistema de costos)."""

import statistics
from contextlib import nullcontext
from datetime import date
from decimal import Decimal

from bitacora.eventos import Accion, Resultado
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol as RolUsuario

from . import calculos
from .exceptions import (
    EstimacionInvalidaError,
    ParametroInvalidoError,
    RondaCerradaError,
    RondaSinAprobarError,
)

ROLES_MODULO = frozenset(
    {RolUsuario.ADMINISTRADOR, RolUsuario.CONTADOR_COSTOS}
)

CLAVE_HORAS_SEMANA = "horas_semana"
CLAVE_SEMANAS_ANIO = "semanas_año"
CLAVE_TASA_CARGAS = "tasa_cargas_patronales"
CLAVE_EFICIENCIA = "eficiencia"
CLAVE_UMBRAL_DISPERSION = "umbral_dispersion_delphi"

PARAMETROS_CALCULO = (
    CLAVE_HORAS_SEMANA,
    CLAVE_SEMANAS_ANIO,
    CLAVE_TASA_CARGAS,
    CLAVE_EFICIENCIA,
    CLAVE_UMBRAL_DISPERSION,
)


class EstimacionService:
    """Estimación por juicio de expertos (método Delphi)."""

    def __init__(self, repositorio, bitacora, transaccion=nullcontext):
        self._repositorio = repositorio
        self._bitacora = bitacora
        self._transaccion = transaccion

    # --- Consultas ---

    def listar_juegos(self, actor):
        self._verificar(actor)
        return self._repositorio.juegos()

    def obtener_juego(self, actor, juego_id):
        self._verificar(actor)
        return self._repositorio.obtener_juego(juego_id)

    def catalogos(self, actor):
        """Roles, expertos y parámetros para los formularios."""
        self._verificar(actor)
        return {
            "roles": list(self._repositorio.roles()),
            "expertos": list(self._repositorio.expertos()),
        }

    def parametros(self, actor):
        self._verificar(actor)
        return self._repositorio.parametros()

    def salarios(self, actor):
        self._verificar(actor)
        return self._repositorio.salarios()

    # --- Altas de catálogo ---

    def crear_juego(self, actor, nombre, fases):
        """Alta de un juego con sus fases de estimación."""
        self._verificar(actor)
        with self._transaccion():
            juego = self._repositorio.guardar_juego(
                self._repositorio.nuevo_juego(nombre.strip())
            )
            for orden, (nombre_fase, _) in enumerate(fases, start=1):
                self._repositorio.guardar_fase(
                    self._repositorio.nueva_fase(
                        juego, nombre_fase.strip(), orden
                    )
                )
            self._registrar(
                Accion.ALTA_JUEGO, actor, f"Juego «{juego.nombre}»"
            )
        return juego

    def crear_rol(self, actor, nombre, nivel):
        self._verificar(actor)
        return self._repositorio.guardar_rol(
            self._repositorio.nuevo_rol(nombre.strip(), nivel)
        )

    def crear_experto(self, actor, nombre):
        self._verificar(actor)
        return self._repositorio.guardar_experto(
            self._repositorio.nuevo_experto(nombre.strip())
        )

    @staticmethod
    def _verificar_solape_vigencia(existentes, desde, hasta, excluir_id=None):
        """Dos vigencias del mismo concepto no se traslapan."""
        for existente in existentes:
            if excluir_id is not None and existente.pk == excluir_id:
                continue
            fin_existente = existente.vigente_hasta or date.max
            fin_nueva = hasta or date.max
            if existente.vigente_desde <= fin_nueva and desde <= fin_existente:
                raise ParametroInvalidoError(
                    "La vigencia se traslapa con otra ya registrada."
                )

    def crear_parametro(self, actor, clave, valor, vigente_desde,
                        vigente_hasta=None, verificado=False):
        self._verificar(actor)
        existentes = [
            p for p in self._repositorio.parametros()
            if p.clave == clave
        ]
        self._verificar_solape_vigencia(
            existentes, vigente_desde, vigente_hasta
        )
        return self._repositorio.guardar_parametro(
            self._repositorio.nuevo_parametro(
                clave=clave, valor=valor, vigente_desde=vigente_desde,
                vigente_hasta=vigente_hasta, verificado=verificado,
            )
        )

    def crear_salario(self, actor, rol_id, salario_bruto, vigente_desde,
                      vigente_hasta=None):
        self._verificar(actor)
        rol = self._repositorio.obtener_rol(rol_id)
        existentes = [
            s for s in self._repositorio.salarios()
            if s.rol_id == rol.pk
        ]
        self._verificar_solape_vigencia(
            existentes, vigente_desde, vigente_hasta
        )
        return self._repositorio.guardar_salario(
            self._repositorio.nuevo_salario(
                rol=rol, salario_bruto=salario_bruto,
                vigente_desde=vigente_desde, vigente_hasta=vigente_hasta,
            )
        )

    # --- Estimaciones Delphi ---

    def registrar_estimacion(self, actor, *, juego_id, fase_id, rol_id,
                             experto_id, ronda, optimista, moda,
                             pesimista, justificacion=""):
        self._verificar(actor)
        self._validar_omp(optimista, moda, pesimista)
        with self._transaccion():
            juego = self._repositorio.obtener_juego(juego_id)
            ronda_db = self._repositorio.ronda_o_nueva(juego, ronda)
            if ronda_db.cerrada:
                raise RondaCerradaError()
            estimacion = self._repositorio.guardar_estimacion(
                self._repositorio.nueva_estimacion(
                    juego=juego,
                    fase=self._repositorio.obtener_fase(fase_id, juego),
                    rol=self._repositorio.obtener_rol(rol_id),
                    experto=self._repositorio.obtener_experto(experto_id),
                    ronda=ronda,
                    optimista=optimista,
                    moda=moda,
                    pesimista=pesimista,
                    justificacion=justificacion,
                )
            )
            self._registrar(
                Accion.REGISTRO_ESTIMACION, actor,
                f"Estimación {estimacion.pk}",
            )
        return estimacion

    def consolidar(self, actor, juego_id, numero, *, fecha=None):
        """Media, mediana y coeficiente de variación por fase y rol.

        El coeficiente de variación se calcula sobre las horas esperadas
        PERT de cada experto. Si supera el umbral, la fase queda marcada
        para una nueva ronda.
        """
        self._verificar(actor)
        juego = self._repositorio.obtener_juego(juego_id)
        ronda = self._repositorio.obtener_ronda(juego, numero)
        estimaciones = list(
            self._repositorio.estimaciones_de(juego, ronda=numero)
        )
        umbral = self._umbral(actor, fecha)
        grupos = self._agrupar(estimaciones)
        return [
            self._consolidar_grupo(grupo, umbral)
            for grupo in grupos.values()
        ]

    def cerrar_ronda(self, actor, juego_id, numero, *, fecha=None):
        """Consolida y cierra la ronda; exige aprobación registrada."""
        self._verificar(actor)
        if actor is None:
            raise RondaSinAprobarError()
        with self._transaccion():
            juego = self._repositorio.obtener_juego(juego_id)
            ronda = self._repositorio.obtener_ronda(juego, numero)
            if ronda.cerrada:
                raise RondaCerradaError()
            consolidado = self.consolidar(actor, juego_id, numero,
                                          fecha=fecha)
            ronda.resultado = consolidado
            ronda.cerrada = True
            ronda.aprobada_por = actor
            self._repositorio.guardar_ronda(ronda)
            self._registrar(
                Accion.CIERRE_RONDA_DELPHI, actor,
                f"Ronda {ronda.juego} #{ronda.numero}",
            )
        return ronda

    def rondas(self, actor, juego_id):
        self._verificar(actor)
        juego = self._repositorio.obtener_juego(juego_id)
        return self._repositorio.rondas_de(juego)

    # --- Consolidación ---

    @staticmethod
    def _agrupar(estimaciones):
        grupos = {}
        for estimacion in estimaciones:
            clave = (estimacion.fase_id, estimacion.rol_id)
            grupos.setdefault(clave, []).append(estimacion)
        return grupos

    def _umbral(self, actor, fecha):
        return self._parametro(actor, CLAVE_UMBRAL_DISPERSION, fecha).valor

    def _parametro(self, actor, clave, fecha):
        self._verificar(actor)
        return self._repositorio.parametro_vigente(
            clave, fecha or date.today()
        )

    @staticmethod
    def _consolidar_grupo(grupo, umbral):
        horas = [
            float(calculos.pert(e.optimista, e.moda, e.pesimista)[0])
            for e in grupo
        ]
        media_f = statistics.fmean(horas)
        mediana_f = statistics.median(horas)
        media = Decimal(str(media_f))
        mediana = Decimal(str(mediana_f))
        if media_f == 0:
            coeficiente = Decimal("0") if not any(horas) else Decimal("1")
        else:
            coeficiente = Decimal(
                str(statistics.pstdev(horas) / media_f)
            )
        requiere = coeficiente > umbral
        optimista = sum((e.optimista for e in grupo), Decimal("0")) / len(grupo)
        moda = sum((e.moda for e in grupo), Decimal("0")) / len(grupo)
        pesimista = sum((e.pesimista for e in grupo), Decimal("0")) / len(grupo)
        esperado, sigma = calculos.pert(optimista, moda, pesimista)
        primera = grupo[0]
        return {
            "fase_id": primera.fase_id,
            "fase": primera.fase.nombre,
            "rol_id": primera.rol_id,
            "rol": str(primera.rol),
            "expertos": len(grupo),
            "horas_E": str(esperado),
            "sigma": str(sigma),
            "media": str(media),
            "mediana": str(mediana),
            "coeficiente_variacion": str(coeficiente),
            "requiere_nueva_ronda": requiere,
        }

    # --- Validaciones y bitácora ---

    @staticmethod
    def _validar_omp(optimista, moda, pesimista):
        valores = (optimista, moda, pesimista)
        if any(v < 0 for v in valores) or not (
            optimista <= moda <= pesimista
        ):
            raise EstimacionInvalidaError()

    def _registrar(self, accion, actor, referencia):
        self._bitacora.registrar(
            accion, Resultado.EXITOSO, actor=actor, referencia=referencia
        )

    @staticmethod
    def _verificar(actor):
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol not in ROLES_MODULO:
            raise RolNoAutorizadoError()
