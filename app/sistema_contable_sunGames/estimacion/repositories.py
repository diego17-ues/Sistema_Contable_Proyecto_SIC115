from django.db.models import Q

from .exceptions import (
    ExpertoNoEncontradoError,
    FaseNoEncontradaError,
    JuegoNoEncontradoError,
    ParametroInvalidoError,
    ParametroNoEncontradoError,
    RolNoEncontradoError,
    RondaNoEncontradaError,
    SalarioNoEncontradoError,
    VersionNoEncontradaError,
)
from .models import (
    CostoDirectoEstimado,
    CostoFabricacion,
    CostoIndirectoEstimado,
    EstimacionExperto,
    Experto,
    FaseEstimacion,
    Juego,
    LineaPresupuesto,
    ParametroVigente,
    RondaDelphi,
    Rol,
    SalarioReferencia,
    VersionPresupuesto,
)


class EstimacionRepository:
    """Consultas ORM del módulo de estimación."""

    # --- Juegos, fases y catálogo de estimación ---

    def juegos(self):
        return Juego.objects.prefetch_related("fases").order_by("nombre")

    def obtener_juego(self, juego_id):
        try:
            return Juego.objects.prefetch_related(
                "fases", "rondas"
            ).get(pk=juego_id)
        except Juego.DoesNotExist as exc:
            raise JuegoNoEncontradoError() from exc

    def juego_nombre_existente(self, nombre, *, excluir_id=None):
        qs = Juego.objects.filter(nombre__iexact=nombre)
        if excluir_id is not None:
            qs = qs.exclude(pk=excluir_id)
        return qs.exists()

    def nuevo_juego(self, nombre):
        return Juego(nombre=nombre)

    def guardar_juego(self, juego):
        juego.save()
        return juego

    def nueva_fase(self, juego, nombre, orden, clasificacion):
        return FaseEstimacion(
            juego=juego, nombre=nombre, orden=orden,
            clasificacion=clasificacion,
        )

    def guardar_fase(self, fase):
        fase.save()
        return fase

    def fases_de(self, juego):
        return FaseEstimacion.objects.filter(juego=juego).order_by(
            "orden", "id"
        )

    def obtener_fase(self, fase_id, juego=None):
        fases = FaseEstimacion.objects.filter(pk=fase_id)
        if juego is not None:
            fases = fases.filter(juego=juego)
        fase = fases.first()
        if fase is None:
            raise FaseNoEncontradaError()
        return fase

    def roles(self):
        return Rol.objects.order_by("nivel", "nombre")

    def obtener_rol(self, rol_id):
        try:
            return Rol.objects.get(pk=rol_id)
        except Rol.DoesNotExist as exc:
            raise RolNoEncontradoError() from exc

    def nuevo_rol(self, nombre, nivel):
        return Rol(nombre=nombre, nivel=nivel)

    def guardar_rol(self, rol):
        rol.save()
        return rol

    def expertos(self):
        return Experto.objects.order_by("nombre")

    def obtener_experto(self, experto_id):
        try:
            return Experto.objects.get(pk=experto_id)
        except Experto.DoesNotExist as exc:
            raise ExpertoNoEncontradoError() from exc

    def nuevo_experto(self, nombre):
        return Experto(nombre=nombre)

    def guardar_experto(self, experto):
        experto.save()
        return experto

    # --- Estimaciones y rondas ---

    def estimaciones_de(self, juego, ronda=None, *, incluir_eliminadas=False):
        estimaciones = EstimacionExperto.objects.filter(
            juego=juego
        ).select_related("fase", "rol", "experto")
        if not incluir_eliminadas:
            estimaciones = estimaciones.filter(eliminado_en__isnull=True)
        if ronda is not None:
            estimaciones = estimaciones.filter(ronda=ronda)
        return estimaciones.order_by(
            "fase__orden", "rol__nivel", "rol__nombre", "experto__nombre"
        )

    def nueva_estimacion(self, **campos):
        return EstimacionExperto(**campos)

    def guardar_estimacion(self, estimacion):
        estimacion.save()
        return estimacion

    def obtener_estimacion(self, estimacion_id, *, juego=None,
                           incluir_eliminada=False):
        qs = EstimacionExperto.objects.select_related(
            "juego", "fase", "rol", "experto"
        )
        if juego is not None:
            qs = qs.filter(juego=juego)
        if not incluir_eliminada:
            qs = qs.filter(eliminado_en__isnull=True)
        return qs.filter(pk=estimacion_id).first()

    def estimaciones_existen(self, juego, rol, experto, ronda):
        return EstimacionExperto.objects.filter(
            juego=juego, rol=rol, experto=experto, ronda=ronda,
            eliminado_en__isnull=True,
        ).exists()

    def estimacion_fase_existe(self, estimacion):
        return EstimacionExperto.objects.filter(
            juego=estimacion.juego,
            fase=estimacion.fase,
            rol=estimacion.rol,
            experto=estimacion.experto,
            ronda=estimacion.ronda,
            eliminado_en__isnull=True,
        ).exclude(pk=estimacion.pk).exists()

    def rondas_de(self, juego):
        return RondaDelphi.objects.filter(juego=juego).order_by("numero")

    def obtener_ronda(self, juego, numero):
        try:
            return RondaDelphi.objects.get(juego=juego, numero=numero)
        except RondaDelphi.DoesNotExist as exc:
            raise RondaNoEncontradaError() from exc

    def ronda_o_nueva(self, juego, numero):
        ronda = RondaDelphi.objects.filter(
            juego=juego, numero=numero
        ).first()
        if ronda is None:
            ronda = RondaDelphi(juego=juego, numero=numero)
            ronda.save()
        return ronda

    def guardar_ronda(self, ronda):
        ronda.save()
        return ronda

    # --- Parámetros y salarios ---

    def parametro_vigente(self, clave, fecha):
        """Parámetro vigente en la fecha; el de mayor inicio que aplique."""
        parametro = (
            ParametroVigente.objects.filter(
                clave=clave, vigente_desde__lte=fecha
            )
            .filter(
                Q(vigente_hasta__isnull=True)
                | Q(vigente_hasta__gte=fecha)
            )
            .order_by("-vigente_desde")
            .first()
        )
        if parametro is None:
            raise ParametroInvalidoError(
                f"No hay parámetro vigente para «{clave}» en {fecha}."
            )
        return parametro

    def parametros(self):
        return ParametroVigente.objects.order_by("clave", "vigente_desde")

    def obtener_parametro(self, parametro_id):
        try:
            return ParametroVigente.objects.get(pk=parametro_id)
        except ParametroVigente.DoesNotExist as exc:
            raise ParametroNoEncontradoError() from exc

    def nuevo_parametro(self, **campos):
        return ParametroVigente(**campos)

    def guardar_parametro(self, parametro):
        parametro.save()
        return parametro

    def salario_vigente(self, rol, fecha):
        salario = (
            SalarioReferencia.objects.filter(
                rol=rol, vigente_desde__lte=fecha
            )
            .filter(
                Q(vigente_hasta__isnull=True)
                | Q(vigente_hasta__gte=fecha)
            )
            .order_by("-vigente_desde")
            .first()
        )
        if salario is None:
            raise SalarioNoEncontradoError()
        return salario

    def salarios(self):
        return SalarioReferencia.objects.select_related(
            "rol"
        ).order_by("rol__nivel", "rol__nombre", "vigente_desde")

    def nuevo_salario(self, **campos):
        return SalarioReferencia(**campos)

    def guardar_salario(self, salario):
        salario.save()
        return salario

    # --- Versiones de presupuesto (E4) ---

    def versiones_de(self, juego, *, incluir_eliminadas=False):
        qs = VersionPresupuesto.objects.filter(juego=juego)
        if not incluir_eliminadas:
            qs = qs.filter(eliminado_en__isnull=True)
        return (
            qs
            .select_related("autor")
            .prefetch_related(
                "lineas__fase", "lineas__rol",
                "costos_directos", "costos_indirectos",
            )
            .order_by("-numero")
        )

    def obtener_version(self, version_id, *, incluir_eliminada=False):
        try:
            qs = VersionPresupuesto.objects.select_related(
                "juego", "autor"
            ).prefetch_related(
                "lineas__fase", "lineas__rol",
                "costos_directos", "costos_indirectos",
            )
            if not incluir_eliminada:
                qs = qs.filter(eliminado_en__isnull=True)
            return qs.get(pk=version_id)
        except VersionPresupuesto.DoesNotExist as exc:
            raise VersionNoEncontradaError() from exc

    def siguiente_numero_version(self, juego):
        numero = VersionPresupuesto.objects.filter(juego=juego).order_by(
            "-numero"
        ).values_list("numero", flat=True).first()
        return (numero or 0) + 1

    def nueva_version(self, juego, numero, autor, snapshot):
        return VersionPresupuesto(
            juego=juego, numero=numero, autor=autor,
            snapshot_parametros=snapshot,
        )

    def guardar_version(self, version):
        version.save()
        return version

    def nueva_linea(self, version, fase, rol, **valores):
        return LineaPresupuesto(
            version=version, fase=fase, rol=rol, **valores
        )

    def guardar_linea(self, linea):
        linea.save()
        return linea

    def nueva_linea_directa(self, version, concepto, monto):
        return CostoDirectoEstimado(
            version=version, concepto=concepto, monto=monto
        )

    def nueva_linea_indirecta(self, version, departamento, monto):
        return CostoIndirectoEstimado(
            version=version, departamento=departamento, monto=monto
        )

    def guardar_costo_directo(self, costo):
        costo.save()
        return costo

    def guardar_costo_indirecto(self, costo):
        costo.save()
        return costo

    # --- Costos de fabricación por juego ---

    def costos_fabricacion_de(self, juego):
        return CostoFabricacion.objects.filter(juego=juego).order_by(
            "tipo", "id"
        )

    def nueva_costo_fabricacion(self, juego, tipo, concepto, monto):
        return CostoFabricacion(
            juego=juego, tipo=tipo, concepto=concepto, monto=monto
        )

    def guardar_costo_fabricacion(self, costo):
        costo.save()
        return costo
