"""Servicios del subsistema de costos (órdenes de trabajo, Etapa 1).

Reglas:
- Cada registro de costo acumula únicamente en la cuenta de costo del
  elemento, mediante el repositorio de la contabilidad general (nunca se
  escribe directo en sus tablas). No hay contrapartida: la orden solo
  acumula en sus cuentas de costo. La contrapartida del pago o del
  pasivo se registra en la contabilidad general.
- Las cuentas salen de ``ConfiguracionCuentaCosto``; ningún código de
  cuenta, tarifa ni porcentaje vive en el código.
- Los registros no se editan ni se borran: se anulan con contra-asiento.
- Período cerrado u orden cerrada rechazan registros nuevos.
- Cada operación lleva clave de idempotencia: repetirla no duplica.
- Todo en ``Decimal``.
"""

from contextlib import nullcontext
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from bitacora.eventos import Accion, Resultado
from libro_mayor.exceptions import FechaInvalidaError, LibroMayorError
from libro_mayor.models import EstadoPeriodo, TipoMovimiento
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from . import calculos
from .exceptions import (
    AsientoDescuadradoError,
    ClaveIdempotenciaError,
    ConfiguracionNoEncontradaError,
    CostosError,
    CuentaNoValidaError,
    DatosInsuficientesError,
    OrdenCerradaError,
    OrdenDuplicadaError,
    OrdenNoEncontradaError,
    PeriodoNoAbiertoError,
    ProcesoNoValidoError,
    RegistroNoEncontradoError,
    RegistroYaAnuladoError,
)
from .models import (
    AsientoCosto,
    CuentaIndirectaExcluida,
    Elemento,
    FuenteIndirecta,
    ReclasificacionCosto,
    RegistroCosto,
)

# El módulo de costos está disponible para Costos y Administración.
ROLES_COSTOS = frozenset({Rol.CONTADOR_COSTOS, Rol.ADMINISTRADOR})


def _verificar(actor):
    if not actor.activo:
        raise UsuarioInactivoError()
    if actor.rol not in ROLES_COSTOS:
        raise RolNoAutorizadoError()


class CostosService:
    """Base: verificación de rol y bitácora."""

    def __init__(self, repositorio, bitacora, transaccion=nullcontext):
        self._repo = repositorio
        self._bitacora = bitacora
        self._transaccion = transaccion

    def puede(self, actor):
        return actor.activo and actor.rol in ROLES_COSTOS

    def _orden(self, orden_id):
        orden = self._repo.obtener_orden(orden_id)
        if orden is None:
            raise OrdenNoEncontradaError("La orden de trabajo no existe.")
        return orden

    def _auditar(self, actor, accion, referencia, detalle=""):
        if self._bitacora is not None:
            self._bitacora.registrar(
                accion, Resultado.EXITOSO, actor=actor,
                referencia=(referencia or "")[:60], detalle=detalle,
            )


class ReclasificacionCostoService(CostosService):
    """Traslada los costos de desarrollo al activo correspondiente."""

    CUENTA_PROCESO = "1106"
    CUENTA_TERMINADO = "1107"

    def __init__(self, repositorio, mayor, bitacora, transaccion=nullcontext):
        super().__init__(repositorio, bitacora, transaccion)
        self._mayor = mayor

    def trasladar_cierre(self, actor, periodo):
        """Capitaliza al cierre los costos de las órdenes del período."""
        ciclo = self._repo.siguiente_ciclo_reclasificacion(periodo)
        for fila in self._repo.costos_pendientes_reclasificar(
                hasta=periodo.fecha_fin, periodo=periodo):
            importe = Decimal(fila["importe"] or 0)
            if importe <= 0:
                continue
            orden = self._repo.obtener_orden(
                fila["orden_id"], incluir_eliminada=True
            )
            if orden is None:
                raise OrdenNoEncontradaError(
                    "No se encontró la orden asociada a un costo del período."
                )
            cuenta_origen = self._cuenta(fila["cuenta_costo__codigo"])
            destino_codigo = (
                self.CUENTA_PROCESO if orden.abierta
                else self.CUENTA_TERMINADO
            )
            self._crear_traslado(
                actor, periodo=periodo, orden=orden,
                cuenta_origen=cuenta_origen,
                cuenta_destino=self._cuenta(destino_codigo),
                importe=importe, tipo=ReclasificacionCosto.TIPO_CIERRE,
                ciclo=ciclo,
                clave=(f"cierre-{periodo.pk}-{ciclo}-{orden.pk}-"
                       f"{cuenta_origen.pk}"),
                fecha=periodo.fecha_fin,
            )

    def revertir_cierre(self, actor, periodo):
        """Revierte las reclasificaciones que afectan el período reabierto."""
        cierres = list(self._repo.traslados_costo(
            periodo=periodo, tipo=ReclasificacionCosto.TIPO_CIERRE,
            solo_activos=True,
        ))
        directas = list(self._repo.traslados_costo(
            periodo=periodo, tipo=ReclasificacionCosto.TIPO_FINALIZACION,
            solo_directos=True, solo_activos=True,
        ))
        derivadas = []
        for cierre in cierres:
            derivadas.extend(self._repo.traslados_costo(
                origen=cierre, tipo=ReclasificacionCosto.TIPO_FINALIZACION,
                solo_activos=True,
            ))

        # Primero se devuelve de terminados a proceso y luego de proceso a
        # las cuentas 4101/4102 para restaurar el saldo original completo.
        for traslado in [*derivadas, *directas, *reversed(cierres)]:
            self._crear_traslado(
                actor, periodo=periodo, orden=traslado.orden,
                cuenta_origen=traslado.cuenta_destino,
                cuenta_destino=traslado.cuenta_origen,
                importe=traslado.importe,
                tipo=ReclasificacionCosto.TIPO_REVERSION,
                ciclo=traslado.ciclo,
                clave=f"reversion-{traslado.pk}",
                fecha=periodo.fecha_fin, revierte=traslado,
            )

    def finalizar_orden(self, actor, orden):
        """Mueve a 1107 los saldos en proceso y costos del período abierto."""
        periodo = self._repo.periodo_abierto_mas_reciente()
        if periodo is None:
            raise PeriodoNoAbiertoError(
                "Abre un período contable antes de finalizar la orden."
            )
        hoy = timezone.localdate()
        fecha = min(max(hoy, periodo.fecha_inicio), periodo.fecha_fin)

        # Costos ya capitalizados como producción en proceso pasan de 1106
        # a 1107. Se guarda el vínculo para que reabrir el cierre de origen
        # revierta también este segundo traslado.
        cierres = self._repo.traslados_costo(
            orden=orden, tipo=ReclasificacionCosto.TIPO_CIERRE,
            cuenta_destino_codigo=self.CUENTA_PROCESO, solo_activos=True,
        )
        for cierre in cierres:
            if self._repo.tiene_finalizacion_derivada_activa(cierre):
                continue
            self._crear_traslado(
                actor, periodo=periodo, orden=orden,
                cuenta_origen=cierre.cuenta_destino,
                cuenta_destino=self._cuenta(self.CUENTA_TERMINADO),
                importe=cierre.importe,
                tipo=ReclasificacionCosto.TIPO_FINALIZACION,
                ciclo=cierre.ciclo,
                clave=f"finaliza-cierre-{cierre.pk}",
                fecha=fecha, origen=cierre,
            )

        # Los costos aún pendientes en 4101/4102 se capitalizan directamente
        # en videojuegos terminados.
        for fila in self._repo.costos_pendientes_reclasificar(
                hasta=fecha, orden=orden):
            cuenta_origen = self._cuenta(fila["cuenta_costo__codigo"])
            importe = Decimal(fila["importe"])
            clave = (f"finaliza-directo-{periodo.pk}-{orden.pk}-"
                     f"{cuenta_origen.pk}")
            self._crear_traslado(
                actor, periodo=periodo, orden=orden,
                cuenta_origen=cuenta_origen,
                cuenta_destino=self._cuenta(self.CUENTA_TERMINADO),
                importe=importe,
                tipo=ReclasificacionCosto.TIPO_FINALIZACION,
                ciclo=1, clave=clave, fecha=fecha,
            )

    def _crear_traslado(self, actor, *, periodo, orden, cuenta_origen,
                        cuenta_destino, importe, tipo, ciclo, clave, fecha,
                        origen=None, revierte=None):
        importe = Decimal(importe).quantize(Decimal("0.01"))
        if importe <= 0:
            return None
        transaccion = self._mayor.crear_transaccion(usuario=actor)
        referencia = f"OT-{orden.pk} · {clave}"[:40]
        concepto = f"Reclasificación de costos OT-{orden.pk}"[:200]
        try:
            self._mayor.crear_movimiento(
                transaccion=transaccion, cuenta=cuenta_origen,
                fecha=fecha, concepto=concepto, referencia=referencia,
                tipo=TipoMovimiento.DIARIO, importe=-importe,
            )
            self._mayor.crear_movimiento(
                transaccion=transaccion, cuenta=cuenta_destino,
                fecha=fecha, concepto=concepto, referencia=referencia,
                tipo=TipoMovimiento.DIARIO, importe=importe,
            )
        except LibroMayorError as exc:
            raise PeriodoNoAbiertoError(str(exc)) from exc
        return self._repo.crear_reclasificacion(
            periodo=periodo, orden=orden, transaccion=transaccion,
            cuenta_origen=cuenta_origen, cuenta_destino=cuenta_destino,
            importe=importe, tipo=tipo, ciclo=ciclo, origen=origen,
            revierte=revierte, clave_idempotencia=clave,
        )

    def _cuenta(self, codigo):
        try:
            cuenta = self._mayor.obtener_cuenta(codigo)
        except LibroMayorError as exc:
            raise CuentaNoValidaError(
                f"La cuenta requerida {codigo} no existe en el catálogo."
            ) from exc
        if (not cuenta.activa or self._mayor.tiene_subcuentas(cuenta)):
            raise CuentaNoValidaError(
                f"La cuenta {codigo} debe estar activa y admitir movimientos."
            )
        return cuenta


class OrdenService(CostosService):
    """Alta y consulta de órdenes de trabajo y su hoja de costos."""

    def __init__(self, repositorio, bitacora, transaccion=nullcontext,
                 total_estimacion=None, reclasificaciones=None):
        super().__init__(repositorio, bitacora, transaccion)
        self._total_estimacion = total_estimacion
        self._reclasificaciones = reclasificaciones

    def resumen_orden(self, orden_id):
        """Totales por elemento y por proceso, horas por proceso, costo
        total, licencias, costo unitario y estimación de referencia."""
        orden = self._orden(orden_id)
        return self._resumen(orden, self._repo.registros_de_orden(orden))

    def evaluar_rendimiento(self, actor, orden_id):
        """Compara la estimación vinculada con los costos vigentes de la OT."""
        _verificar(actor)
        orden = self._orden(orden_id)
        if orden.estimacion_ref is None:
            raise DatosInsuficientesError(
                "Vincula una estimación aprobada antes de evaluar la orden."
            )
        if self._total_estimacion is None:
            raise DatosInsuficientesError(
                "No está disponible el total de la estimación vinculada."
            )

        registros = list(self._repo.registros_de_orden(orden))
        if not any(registro.vigente for registro in registros):
            raise DatosInsuficientesError(
                "La evaluación requiere al menos un costo vigente."
            )

        _, _, total_real = calculos.resumir(registros, Elemento.values)
        total_estimado = self._total_estimacion(orden.estimacion_ref)
        return calculos.comparar_estimado_real(total_estimado, total_real)

    def resultados_rendimiento(self, actor):
        """Lista estimación y costo real vigente por orden de trabajo."""
        _verificar(actor)
        resultados = []
        for orden in self._repo.ordenes_rendimiento():
            total_real = orden.total_vigente
            total_estimado = None
            if (orden.estimacion_ref is not None
                    and self._total_estimacion is not None):
                total_estimado = self._total_estimacion(orden.estimacion_ref)

            evaluacion = None
            if total_estimado is not None and total_real is not None:
                evaluacion = calculos.comparar_estimado_real(
                    total_estimado, total_real
                )

            resultados.append({
                "orden": orden,
                "total_estimado": total_estimado,
                "total_real": total_real,
                "evaluacion": evaluacion,
            })
        return resultados

    def resumen_dashboard(self, actor):
        """Resumen de lectura para Costos y para el Dashboard General."""
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol not in {
            Rol.CONTADOR_COSTOS, Rol.CONTADOR_GENERAL, Rol.ADMINISTRADOR
        }:
            raise RolNoAutorizadoError()

        resumen = self._repo.resumen_dashboard()
        recientes = [
            self._rendimiento_dashboard(orden)
            for orden in resumen["finalizadas_recientes"]
        ]
        ultima_registrada = resumen["ultima_registrada"]
        return {
            "ordenes_pendientes": resumen["pendientes"],
            "ordenes_finalizadas": resumen["finalizadas"],
            "ultima_orden": recientes[0] if recientes else None,
            "ordenes_finalizadas_recientes": recientes,
            "ultima_orden_registrada": (
                self._rendimiento_dashboard(ultima_registrada)
                if ultima_registrada is not None else None
            ),
        }

    def _rendimiento_dashboard(self, orden):
        total_real = orden.total_vigente
        version = orden.estimacion_ref
        total_estimado = (
            self._total_estimacion(version)
            if version is not None and self._total_estimacion is not None
            else None
        )
        evaluacion = None
        if total_estimado is not None and total_real is not None:
            evaluacion = calculos.comparar_estimado_real(
                total_estimado, total_real
            )
        return {
            "orden": orden,
            "total_real": total_real,
            "total_estimado": total_estimado,
            "evaluacion": evaluacion,
        }

    def hoja_costos(self, actor, orden_id):
        _verificar(actor)
        orden = self._orden(orden_id)
        registros = list(self._repo.registros_de_orden(orden))
        resumen = self._resumen(orden, registros)
        secciones = [
            {"elemento": elemento.value, "nombre": elemento.label,
             "registros": [r for r in registros
                           if r.elemento == elemento.value],
             "subtotal": resumen["por_elemento"][elemento.value]}
            for elemento in Elemento
        ]
        return orden, secciones, resumen

    def versiones_disponibles(self, actor, *, orden_id=None):
        _verificar(actor)
        if orden_id is not None:
            self._orden(orden_id)
        return list(self._repo.versiones_disponibles(
            orden_id=orden_id
        ))

    def actualizar_licencias(self, actor, orden_id, licencias):
        _verificar(actor)
        if licencias is None or int(licencias) <= 0:
            raise DatosInsuficientesError(
                "Las licencias estimadas deben ser mayores que cero.",
                campo="licencias_estimadas",
            )
        orden = self._orden(orden_id)
        orden.licencias_estimadas = int(licencias)
        self._repo.guardar_orden(orden)
        self._auditar(actor, Accion.ORDEN_TRABAJO, f"OT {orden.pk}",
                      f"Licencias estimadas: {orden.licencias_estimadas}")
        return orden

    def vincular_estimacion(self, actor, orden_id, version_id):
        """Vincula una versión disponible y aprobada o vigente."""
        _verificar(actor)
        orden = self._orden(orden_id)
        version = None
        if version_id:
            version = self._repo.obtener_version_disponible(
                version_id, orden_id=orden.pk
            )
            if version is None:
                raise DatosInsuficientesError(
                    "La estimación no está disponible o ya pertenece a "
                    "otra orden.", campo="version",
                )
        try:
            with self._transaccion():
                orden.estimacion_ref = version
                self._repo.guardar_orden(orden)
                self._auditar(
                    actor, Accion.ORDEN_TRABAJO, f"OT {orden.pk}",
                    "Estimación de referencia: "
                    f"{version.pk if version else '—'}",
                )
        except IntegrityError as exc:
            if (version_id and self._repo.obtener_version_disponible(
                    version_id, orden_id=orden.pk) is None):
                raise DatosInsuficientesError(
                    "La estimación ya fue vinculada a otra orden.",
                    campo="version",
                ) from exc
            raise
        return orden

    def _resumen(self, orden, registros):
        por_elemento, por_proceso, total = calculos.resumir(
            registros, Elemento.values
        )
        version = orden.estimacion_ref
        total_estimado = None
        if version is not None and self._total_estimacion is not None:
            total_estimado = self._total_estimacion(version)
        return {
            "por_elemento": por_elemento,
            "por_proceso": [
                {"proceso": f["proceso"], "importe": f["importe"]}
                for f in por_proceso
            ],
            "horas_por_proceso": [
                {"proceso": f["proceso"], "horas": f["horas"]}
                for f in por_proceso if f["horas"]
            ],
            "total": total,
            "licencias_estimadas": orden.licencias_estimadas,
            "costo_unitario": calculos.costo_unitario(
                total, orden.licencias_estimadas
            ),
            "estimacion_ref": version,
            "total_estimado": total_estimado,
        }

    def listar(self, actor, *, estado=None, incluir_eliminadas=False):
        _verificar(actor)
        return list(self._repo.ordenes(
            estado=estado, incluir_eliminadas=incluir_eliminadas
        ))

    def detalle(self, actor, orden_id):
        _verificar(actor)
        return self._orden(orden_id)

    def registros(self, actor, orden):
        _verificar(actor)
        return list(self._repo.registros_de_orden(orden))

    def crear_orden(self, actor, *, nombre_juego=None, fecha_inicio,
                    estimacion_id=None):
        _verificar(actor)
        if fecha_inicio is None:
            raise DatosInsuficientesError(
                "Indica la fecha de inicio.", campo="fecha_inicio"
            )
        try:
            with self._transaccion():
                version = None
                if estimacion_id:
                    version = self._repo.obtener_version_disponible(
                        estimacion_id
                    )
                    if version is None:
                        raise DatosInsuficientesError(
                            "La estimación no está disponible o ya fue "
                            "vinculada a otra orden.", campo="estimacion",
                        )
                    nombre = version.juego.nombre
                else:
                    nombre = (nombre_juego or "").strip()
                    if not nombre:
                        raise DatosInsuficientesError(
                            "Indica el juego de la orden o selecciona una "
                            "estimación.", campo="nombre_juego"
                        )

                juego = self._repo.juego_por_nombre(nombre)
                if juego is None:
                    juego = self._repo.crear_juego(nombre=nombre)
                elif self._repo.orden_por_juego(juego) is not None:
                    raise OrdenDuplicadaError(
                        "Ese juego ya tiene una orden de trabajo.",
                        campo="nombre_juego",
                    )
                orden = self._repo.crear_orden(
                    juego=juego, fecha_inicio=fecha_inicio, usuario=actor,
                    estimacion_ref=version,
                )
                detalle = "Alta de orden"
                if version is not None:
                    detalle += f" · estimación: {version.pk}"
                self._auditar(
                    actor, Accion.ORDEN_TRABAJO,
                    f"OT {orden.pk} · {juego.nombre}", detalle,
                )
        except IntegrityError as exc:
            if (estimacion_id and self._repo.obtener_version_disponible(
                    estimacion_id) is None):
                raise DatosInsuficientesError(
                    "La estimación ya fue vinculada a otra orden.",
                    campo="estimacion",
                ) from exc
            raise
        return orden

    def actualizar_orden(self, actor, orden_id, *, nombre_juego,
                         fecha_inicio, estimacion_id=None,
                         licencias_estimadas=None):
        _verificar(actor)
        orden = self._orden(orden_id)
        if fecha_inicio is None:
            raise DatosInsuficientesError(
                "Indica la fecha de inicio.", campo="fecha_inicio"
            )
        primera_fecha = self._repo.primera_fecha_registro_orden(orden)
        if primera_fecha and fecha_inicio > primera_fecha:
            raise DatosInsuficientesError(
                "La fecha de inicio no puede ser posterior al primer costo "
                "registrado.", campo="fecha_inicio",
            )

        version = None
        if estimacion_id:
            version = self._repo.obtener_version_disponible(
                estimacion_id, orden_id=orden.pk
            )
            if (version is None
                    and int(estimacion_id) == orden.estimacion_ref_id):
                version = orden.estimacion_ref
            if version is None:
                raise DatosInsuficientesError(
                    "La estimación no está disponible o pertenece a otra "
                    "orden.", campo="estimacion",
                )
            nombre = version.juego.nombre
        else:
            nombre = (nombre_juego or "").strip()
            if not nombre:
                raise DatosInsuficientesError(
                    "Indica el nombre del juego o selecciona una "
                    "estimación.", campo="nombre_juego",
                )

        juego_existente = self._repo.juego_por_nombre(nombre)
        if (juego_existente is not None
                and juego_existente.pk != orden.juego_id):
            raise OrdenDuplicadaError(
                "Ya existe otro juego con ese nombre.",
                campo="nombre_juego",
            )
        if licencias_estimadas not in (None, ""):
            if int(licencias_estimadas) <= 0:
                raise DatosInsuficientesError(
                    "Las licencias estimadas deben ser mayores que cero.",
                    campo="licencias_estimadas",
                )

        with self._transaccion():
            orden.juego.nombre = nombre
            self._repo.guardar_juego(orden.juego)
            orden.fecha_inicio = fecha_inicio
            orden.estimacion_ref = version
            if licencias_estimadas not in (None, ""):
                orden.licencias_estimadas = int(licencias_estimadas)
            self._repo.guardar_orden(orden)
            self._auditar(
                actor, Accion.ORDEN_TRABAJO, f"OT {orden.pk}",
                "Modificación de orden de trabajo.",
            )
        return orden

    def finalizar(self, actor, orden_id):
        """Finaliza la OT y traslada sus costos capitalizados a 1107."""
        _verificar(actor)
        orden = self._orden(orden_id)
        if not orden.abierta:
            raise OrdenCerradaError("La orden de trabajo ya está finalizada.")
        if self._reclasificaciones is None:
            raise DatosInsuficientesError(
                "No está disponible el servicio de reclasificación de costos."
            )
        with self._transaccion():
            self._reclasificaciones.finalizar_orden(actor, orden)
            orden.estado = orden.ESTADO_CERRADA
            self._repo.guardar_orden(orden)
            self._auditar(
                actor, Accion.ORDEN_TRABAJO, f"OT {orden.pk}",
                "Orden finalizada; costos trasladados a videojuegos "
                "terminados.",
            )
        return orden

    def eliminar(self, actor, orden_id):
        _verificar(actor)
        orden = self._repo.obtener_orden(
            orden_id, incluir_eliminada=True
        )
        if orden is None:
            raise OrdenNoEncontradaError("La orden de trabajo no existe.")
        if orden.eliminada:
            return orden
        with self._transaccion():
            orden.eliminado_en = timezone.now()
            orden.eliminado_por = actor
            self._repo.guardar_orden(orden)
            self._auditar(
                actor, Accion.ORDEN_TRABAJO, f"OT {orden.pk}",
                "Baja lógica; se conservan la orden, costos y asientos.",
            )
        return orden

    def restaurar(self, actor, orden_id):
        _verificar(actor)
        orden = self._repo.obtener_orden(
            orden_id, incluir_eliminada=True
        )
        if orden is None:
            raise OrdenNoEncontradaError("La orden de trabajo no existe.")
        if not orden.eliminada:
            return orden
        if self._repo.hay_otra_orden_activa(orden):
            raise OrdenDuplicadaError(
                "Ya existe una orden activa para este juego. Archívala "
                "antes de restaurar la orden anterior."
            )
        if self._repo.estimacion_en_otra_orden_activa(orden):
            raise DatosInsuficientesError(
                "La estimación ya está vinculada a otra orden activa."
            )
        with self._transaccion():
            orden.eliminado_en = None
            orden.eliminado_por = None
            self._repo.guardar_orden(orden)
            self._auditar(
                actor, Accion.ORDEN_TRABAJO, f"OT {orden.pk}",
                "Restauración de la orden archivada.",
            )
        return orden


class RegistroCostoService(CostosService):
    """Registro y anulación de los tres elementos del costo con su
    asiento en el Libro Mayor."""

    def __init__(self, repositorio, mayor, bitacora,
                 transaccion=nullcontext, hoy=timezone.localdate):
        super().__init__(repositorio, bitacora, transaccion)
        self._mayor = mayor
        self._hoy = hoy

    # ---- consultas para la presentación ----
    def configuracion(self, actor, elemento):
        _verificar(actor)
        return self._config(elemento)

    def configuraciones_disponibles(self, actor):
        """Elementos con configuración; los ausentes quedan bloqueados."""
        _verificar(actor)
        return {c.elemento: c for c in self._repo.configuraciones()}

    def procesos(self, actor):
        _verificar(actor)
        return list(self._repo.procesos(solo_activos=True))

    def vista_previa_anulacion(self, actor, registro_id):
        """Líneas del contra-asiento que generaría la anulación."""
        _verificar(actor)
        registro = self._registro(registro_id)
        return registro, self._lineas_anulacion(registro)

    # ---- comandos ----
    def registrar_mano_obra(self, actor, *, orden_id, fecha, proceso_id,
                            horas, costo_hora, clave):
        _verificar(actor)
        existente = self._repetido(clave, orden_id)
        if existente is not None:
            return existente
        proceso = self._proceso(proceso_id, obligatorio=True)
        horas, costo_hora = Decimal(horas or 0), Decimal(costo_hora or 0)
        if horas <= 0:
            raise DatosInsuficientesError(
                "Las horas deben ser mayores que cero.", campo="horas"
            )
        if costo_hora <= 0:
            raise DatosInsuficientesError(
                "El costo por hora debe ser mayor que cero.",
                campo="costo_hora",
            )
        importe = calculos.importe_mano_obra(horas, costo_hora)
        if importe <= 0:
            raise DatosInsuficientesError(
                "El importe (horas × costo por hora) debe ser de al menos "
                "USD 0.01.", campo="horas",
            )
        return self._registrar(
            actor, elemento=Elemento.MANO_OBRA, orden_id=orden_id,
            fecha=fecha, proceso=proceso,
            descripcion=f"Mano de obra · {proceso.nombre}",
            importe=importe, clave=clave,
            horas=horas, costo_hora=costo_hora,
        )

    def registrar_costo(self, actor, *, elemento, orden_id, fecha,
                        proceso_id, descripcion, importe, clave):
        """Costo directo o indirecto (proceso opcional)."""
        _verificar(actor)
        if elemento not in (Elemento.DIRECTO, Elemento.INDIRECTO):
            raise DatosInsuficientesError("Elemento del costo no válido.")
        existente = self._repetido(clave, orden_id)
        if existente is not None:
            return existente
        proceso = self._proceso(proceso_id, obligatorio=False)
        descripcion = (descripcion or "").strip()
        if not descripcion:
            raise DatosInsuficientesError(
                "Describe el costo.", campo="descripcion"
            )
        importe = calculos.a_centavos(importe or 0)
        if importe <= 0:
            raise DatosInsuficientesError(
                "El monto debe ser mayor que cero.", campo="importe"
            )
        return self._registrar(
            actor, elemento=elemento, orden_id=orden_id, fecha=fecha,
            proceso=proceso, descripcion=descripcion,
            importe=calculos.a_centavos(importe), clave=clave,
        )

    def anular(self, actor, *, registro_id, motivo, clave):
        _verificar(actor)
        previo = self._repo.asiento_por_clave(clave)
        if previo is not None:
            if (previo.tipo == AsientoCosto.TIPO_ANULACION
                    and previo.registro_id == registro_id):
                return previo.registro
            raise ClaveIdempotenciaError(
                "La solicitud ya se usó para otra operación."
            )
        registro = self._registro(registro_id)
        if not registro.vigente:
            raise RegistroYaAnuladoError("El registro ya está anulado.")
        if registro.es_automatico:
            raise DatosInsuficientesError(
                "Los indirectos automáticos se revierten desde la pantalla "
                "del período, no por orden individual."
            )
        motivo = (motivo or "").strip()
        if not motivo:
            raise DatosInsuficientesError(
                "Indica el motivo de la anulación.", campo="motivo"
            )
        fecha = self._hoy()
        self._verificar_periodo(fecha)
        lineas = self._lineas_anulacion(registro)
        try:
            return self._anular(actor, registro, lineas, fecha, motivo,
                                clave)
        except IntegrityError:
            previo = self._repo.asiento_por_clave(clave)
            if previo is None or previo.registro_id != registro.pk:
                raise RegistroYaAnuladoError(
                    "El registro ya está anulado."
                ) from None
            return previo.registro

    def _anular(self, actor, registro, lineas, fecha, motivo, clave):
        with self._transaccion():
            self._asentar(
                actor, registro, lineas, fecha=fecha,
                tipo=AsientoCosto.TIPO_ANULACION,
                tipo_movimiento=TipoMovimiento.AJUSTE,
                concepto=(f"Anulación registro {registro.pk} · "
                          f"{motivo}"), clave=clave,
            )
            registro.estado = RegistroCosto.ESTADO_ANULADO
            registro.motivo_anulacion = motivo[:200]
            registro.anulado_por = actor
            registro.anulado_en = timezone.now()
            self._repo.guardar_registro(registro)
            self._auditar(
                actor, Accion.CARGO_ORDEN,
                f"OT {registro.orden_id} · anula registro {registro.pk}",
                f"Anulación: {motivo}"[:200],
            )
        return registro

    # ---- auxiliares ----
    def _registrar(self, actor, *, elemento, orden_id, fecha, proceso,
                   descripcion, importe, clave,
                   horas=None, costo_hora=None):
        orden = self._orden(orden_id)
        if not orden.abierta:
            raise OrdenCerradaError(
                "La orden de trabajo está cerrada; no admite registros."
            )
        if fecha is None:
            raise DatosInsuficientesError("Indica la fecha.", campo="fecha")
        self._verificar_periodo(fecha)
        config = self._config(elemento)
        cuenta_costo = self._cuenta_valida(config.cuenta_costo)
        lineas = calculos.linea_acumulacion(cuenta_costo, importe)
        try:
            with self._transaccion():
                registro = self._repo.crear_registro(
                    orden=orden, elemento=elemento, fecha=fecha,
                    proceso=proceso, descripcion=descripcion[:200],
                    horas=horas, costo_hora=costo_hora, importe=importe,
                    cuenta_costo=cuenta_costo,
                    clave_idempotencia=clave, usuario=actor,
                )
                self._asentar(
                    actor, registro, lineas, fecha=fecha,
                    tipo=AsientoCosto.TIPO_REGISTRO,
                    tipo_movimiento=TipoMovimiento.DIARIO,
                    concepto=(f"{registro.get_elemento_display()} · "
                              f"{descripcion}"),
                    clave=clave,
                )
                self._auditar(
                    actor, Accion.CARGO_ORDEN,
                    f"OT {orden.pk} · registro {registro.pk}",
                    f"{registro.get_elemento_display()} ${importe}",
                )
        except IntegrityError:
            existente = self._repo.registro_por_clave(clave)
            if existente is None:
                raise
            return existente
        return registro

    def _asentar(self, actor, registro, lineas, *, fecha, tipo,
                 tipo_movimiento, concepto, clave):
        auxiliar = f"OT-{registro.orden_id}"
        try:
            transaccion = self._mayor.crear_transaccion(usuario=actor)
            for cuenta, importe in lineas:
                self._mayor.crear_movimiento(
                    transaccion=transaccion, cuenta=cuenta, fecha=fecha,
                    concepto=f"{auxiliar} · {concepto}"[:200],
                    referencia=f"{auxiliar} · R{registro.pk}"[:40],
                    tipo=tipo_movimiento, importe=importe,
                )
        except LibroMayorError as exc:
            raise PeriodoNoAbiertoError(str(exc)) from exc
        return self._repo.crear_asiento(
            transaccion=transaccion, tipo=tipo, orden_id=registro.orden_id,
            registro=registro, clave_idempotencia=clave,
        )

    def _lineas_anulacion(self, registro):
        asiento_original = self._repo.asiento_por_clave(
            registro.clave_idempotencia
        )
        if asiento_original is not None:
            movimientos = self._repo.movimientos_de(
                asiento_original.transaccion_id
            )
            if movimientos:
                originales = [(m.cuenta, Decimal(m.importe))
                              for m in movimientos]
                return calculos.lineas_contrarias(originales)
        raise ConfiguracionNoEncontradaError(
            "No se encontró el asiento original para revertir el registro."
        )

    def _repetido(self, clave, orden_id):
        if not clave:
            raise DatosInsuficientesError(
                "Falta la clave de la solicitud; recarga el formulario."
            )
        existente = self._repo.registro_por_clave(clave)
        if existente is not None and existente.orden_id != orden_id:
            raise ClaveIdempotenciaError(
                "La solicitud ya se usó para otra orden."
            )
        return existente

    def _registro(self, registro_id):
        registro = self._repo.obtener_registro(registro_id)
        if registro is None:
            raise RegistroNoEncontradoError("El registro no existe.")
        return registro

    def _proceso(self, proceso_id, *, obligatorio):
        if not proceso_id:
            if obligatorio:
                raise ProcesoNoValidoError(
                    "Selecciona el proceso.", campo="proceso"
                )
            return None
        proceso = self._repo.obtener_proceso(proceso_id)
        if proceso is None or not proceso.activo:
            raise ProcesoNoValidoError(
                "El proceso no existe o está inactivo.", campo="proceso"
            )
        return proceso

    def _verificar_periodo(self, fecha):
        try:
            periodo = self._mayor.periodo_de(fecha)
        except FechaInvalidaError as exc:
            raise PeriodoNoAbiertoError(
                "No hay un período contable que cubra la fecha.",
                campo="fecha",
            ) from exc
        if periodo.cerrado:
            raise PeriodoNoAbiertoError(
                "El período contable de la fecha está cerrado.",
                campo="fecha",
            )

    def _config(self, elemento):
        config = self._repo.configuracion(elemento)
        if config is None:
            raise ConfiguracionNoEncontradaError(
                "No hay cuentas configuradas para "
                f"«{Elemento(elemento).label}»; el registro está bloqueado "
                "hasta configurarlas en Catálogos."
            )
        return config

    def _cuenta_valida(self, cuenta):
        if (cuenta is None or not cuenta.activa
                or self._mayor.tiene_subcuentas(cuenta)):
            raise CuentaNoValidaError(
                "La cuenta configurada no admite registros."
            )
        return cuenta

class CatalogoCostosService(CostosService):
    """Procesos y configuración de cuentas por elemento."""

    def procesos(self, actor):
        _verificar(actor)
        return list(self._repo.procesos())

    def crear_proceso(self, actor, *, nombre, descripcion="",
                      costo_hora=None):
        _verificar(actor)
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInsuficientesError("Indica el nombre.",
                                          campo="nombre")
        try:
            with self._transaccion():
                proceso = self._repo.crear_proceso(
                    nombre=nombre, descripcion=descripcion or "",
                    costo_hora=costo_hora,
                )
        except IntegrityError as exc:
            raise CostosError("Ya existe un proceso con ese nombre.",
                              campo="nombre") from exc
        self._auditar(actor, Accion.CATALOGO_COSTOS,
                      f"Proceso {proceso.nombre}", "Alta de proceso")
        return proceso

    def actualizar_proceso(self, actor, proceso_id, *, costo_hora, activo):
        _verificar(actor)
        proceso = self._repo.obtener_proceso(proceso_id)
        if proceso is None:
            raise ProcesoNoValidoError("El proceso no existe.")
        proceso.costo_hora = costo_hora
        proceso.activo = activo
        self._repo.guardar_proceso(proceso)
        self._auditar(actor, Accion.CATALOGO_COSTOS,
                      f"Proceso {proceso.nombre}",
                      f"Costo/hora {costo_hora} · activo {activo}")
        return proceso

    def configuraciones(self, actor):
        _verificar(actor)
        return {c.elemento: c for c in self._repo.configuraciones()}

    def cuentas(self, actor):
        _verificar(actor)
        return list(self._repo.cuentas_posteables())

    def fuentes_indirectas(self, actor):
        _verificar(actor)
        return list(self._repo.fuentes_indirectas())

    def cuentas_fuentes_disponibles(self, actor):
        _verificar(actor)
        return list(self._repo.cuentas_fuentes_disponibles())

    def cuentas_indirectas_excluidas(self, actor):
        _verificar(actor)
        return list(self._repo.cuentas_indirectas_excluidas())

    def crear_fuente_indirecta(self, actor, *, nombre, tipo, cuenta,
                               proceso=None, exclusiva_desarrollo=False):
        _verificar(actor)
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInsuficientesError(
                "Indica el nombre de la fuente.", campo="nombre"
            )
        if tipo not in FuenteIndirecta.Tipo.values:
            raise DatosInsuficientesError(
                "Selecciona un tipo de fuente válido.", campo="tipo"
            )
        if proceso is not None and not proceso.activo:
            raise ProcesoNoValidoError(
                "El proceso asignado está inactivo.", campo="proceso"
            )
        if not exclusiva_desarrollo:
            raise DatosInsuficientesError(
                "Solo se pueden aplicar cuentas dedicadas exclusivamente "
                "a costos de desarrollo.", campo="exclusiva_desarrollo"
            )
        if cuenta is None or not cuenta.activa:
            raise CuentaNoValidaError(
                "La cuenta de origen no existe o está inactiva.",
                campo="cuenta_origen",
            )
        if cuenta.rubro.codigo != "4":
            raise CuentaNoValidaError(
                "El origen debe ser una cuenta de costos o gastos.",
                campo="cuenta_origen",
            )
        if self._repo.cuenta_indirecta_excluida(cuenta):
            raise CuentaNoValidaError(
                "La cuenta está excluida de la distribución automática.",
                campo="cuenta_origen",
            )
        existente = self._repo.fuentes_indirectas().filter(
            cuenta_origen=cuenta
        ).first()
        if existente is not None:
            raise CuentaNoValidaError(
                "La cuenta ya está registrada como fuente indirecta.",
                campo="cuenta_origen",
            )
        try:
            with self._transaccion():
                fuente = self._repo.crear_fuente_indirecta(
                    nombre=nombre, tipo=tipo, cuenta_origen=cuenta,
                    proceso=proceso, exclusiva_desarrollo=True, activa=True,
                )
                self._auditar(
                    actor, Accion.CATALOGO_COSTOS,
                    f"Fuente indirecta {fuente.pk}",
                    f"{fuente.nombre} · cuenta {cuenta.codigo}",
                )
        except IntegrityError as exc:
            raise CuentaNoValidaError(
                "La cuenta ya está registrada como fuente indirecta."
            ) from exc
        return fuente

    def excluir_cuenta_indirecta(self, actor, *, cuenta, motivo):
        _verificar(actor)
        motivo = (motivo or "").strip()
        if cuenta is None or not cuenta.activa:
            raise CuentaNoValidaError("Selecciona una cuenta activa.")
        if not motivo:
            raise DatosInsuficientesError(
                "Describe por qué se excluye esta cuenta.", campo="motivo"
            )
        fuente = self._repo.fuentes_indirectas().filter(
            cuenta_origen=cuenta
        ).first()
        try:
            with self._transaccion():
                if fuente is not None:
                    fuente.activa = False
                    self._repo.guardar_fuente_indirecta(fuente)
                exclusion = self._repo.excluir_cuenta_indirecta(
                    cuenta=cuenta, motivo=motivo, actor=actor
                )
                self._auditar(
                    actor, Accion.CATALOGO_COSTOS,
                    f"Cuenta indirecta excluida {cuenta.codigo}",
                    motivo[:200],
                )
        except IntegrityError as exc:
            raise CuentaNoValidaError(
                "La cuenta ya está en la lista de exclusión."
            ) from exc
        return exclusion

    def quitar_exclusion_indirecta(self, actor, exclusion_id):
        _verificar(actor)
        exclusion = next((e for e in self._repo.cuentas_indirectas_excluidas()
                          if e.pk == exclusion_id), None)
        if exclusion is None:
            raise DatosInsuficientesError(
                "La cuenta excluida ya no existe."
            )
        cuenta = exclusion.cuenta
        with self._transaccion():
            self._repo.eliminar_exclusion_indirecta(exclusion)
            fuente = self._repo.fuentes_indirectas().filter(
                cuenta_origen=cuenta
            ).first()
            if fuente is not None and fuente.exclusiva_desarrollo:
                fuente.activa = True
                self._repo.guardar_fuente_indirecta(fuente)
            self._auditar(
                actor, Accion.CATALOGO_COSTOS,
                f"Cuenta indirecta habilitada {cuenta.codigo}",
                "Eliminada de la lista de exclusión",
            )
        return cuenta

    def guardar_configuracion(self, actor, *, elemento, cuenta_costo):
        _verificar(actor)
        if elemento not in Elemento.values:
            raise DatosInsuficientesError("Elemento del costo no válido.")
        if cuenta_costo is None or not cuenta_costo.activa:
            raise CuentaNoValidaError(
                "La cuenta de costo no existe o está inactiva.",
                campo="cuenta_costo",
            )
        with self._transaccion():
            config = self._repo.guardar_configuracion(
                elemento=elemento, cuenta_costo=cuenta_costo,
            )
            self._auditar(
                actor, Accion.CATALOGO_COSTOS,
                f"Cuentas {Elemento(elemento).label}",
                f"Cuenta de costo {cuenta_costo.codigo}",
            )
        return config


class AplicacionIndirectosService(CostosService):
    """Vista previa, distribución y asiento de indirectos por horas."""

    def __init__(self, repositorio, mayor, bitacora,
                 transaccion=nullcontext):
        super().__init__(repositorio, bitacora, transaccion)
        self._mayor = mayor

    def periodos(self, actor):
        _verificar(actor)
        return list(self._repo.periodos_contables())

    def previsualizar(self, actor, periodo_id):
        _verificar(actor)
        periodo = self._periodo(periodo_id)
        existentes = list(self._repo.registros_indirectos_periodo(periodo))
        por_fuente = {}
        for registro in existentes:
            por_fuente.setdefault(registro.fuente_indirecta_id, []).append(
                registro
            )

        alertas = []
        fuentes_resumen = []
        distribucion = []
        total_pool = Decimal("0.00")
        total_distribuido = Decimal("0.00")
        fuentes = list(self._repo.fuentes_indirectas(solo_activas=True))
        if not fuentes:
            alertas.append(
                "No hay fuentes indirectas exclusivas de desarrollo "
                "configuradas. Las cuentas compartidas quedan fuera."
            )

        for fuente in fuentes:
            previa = por_fuente.get(fuente.pk, [])
            if previa:
                activas = [r for r in previa if r.vigente]
                importe = sum((r.importe for r in activas), Decimal("0.00"))
                total_pool += sum(
                    (r.importe for r in previa), Decimal("0.00")
                )
                total_distribuido += importe
                fuentes_resumen.append({
                    "fuente": fuente,
                    "pool": sum((r.importe for r in previa),
                                Decimal("0.00")),
                    "horas": sum((r.horas or Decimal("0") for r in activas),
                                 Decimal("0")),
                    "distribuido": importe,
                    "estado": "APLICADA" if activas else "REVERTIDA",
                })
                if not activas:
                    alertas.append(
                        f"{fuente.nombre}: la aplicación fue revertida; "
                        "no se vuelve a aplicar para evitar duplicados."
                    )
                continue

            if self._repo.cuenta_indirecta_excluida(fuente.cuenta_origen):
                alertas.append(
                    f"{fuente.nombre}: su cuenta está excluida y no se "
                    "aplicará."
                )
                continue
            if not fuente.cuenta_origen.activa:
                alertas.append(
                    f"{fuente.nombre}: la cuenta de origen está inactiva."
                )
                continue

            pool = Decimal(self._repo.saldo_cuenta_periodo(
                fuente.cuenta_origen, periodo
            ))
            if pool <= 0:
                alertas.append(
                    f"{fuente.nombre}: no tiene saldo neto deudor en el "
                    "período."
                )
                fuentes_resumen.append({
                    "fuente": fuente, "pool": pool,
                    "horas": Decimal("0"),
                    "distribuido": Decimal("0.00"),
                    "estado": "SIN SALDO",
                })
                continue

            horas_ordenes = self._repo.horas_por_orden_periodo(
                periodo, proceso=fuente.proceso
            )
            horas = {
                orden.pk: Decimal(orden.horas)
                for orden in horas_ordenes
            }
            total_horas = sum(horas.values(), Decimal("0"))
            total_pool += pool
            if total_horas <= 0:
                alertas.append(
                    f"{fuente.nombre}: hay ${pool:.2f} en el pool, pero "
                    "ninguna orden abierta tiene horas elegibles; queda "
                    "como gasto del período."
                )
                fuentes_resumen.append({
                    "fuente": fuente, "pool": pool,
                    "horas": total_horas,
                    "distribuido": Decimal("0.00"), "estado": "SIN HORAS",
                })
                continue

            asignaciones = calculos.distribuir_por_horas(pool, horas)
            total_fuente = sum(asignaciones.values(), Decimal("0.00"))
            total_distribuido += total_fuente
            nombres = {orden.pk: orden.juego.nombre
                       for orden in horas_ordenes}
            for orden in horas_ordenes:
                importe = asignaciones.get(orden.pk, Decimal("0.00"))
                if importe <= 0:
                    continue
                distribucion.append({
                    "fuente": fuente,
                    "orden_id": orden.pk,
                    "juego": nombres[orden.pk],
                    "horas": horas[orden.pk],
                    "tasa": pool / total_horas,
                    "importe": importe,
                })
            fuentes_resumen.append({
                "fuente": fuente, "pool": pool, "horas": total_horas,
                "tasa": pool / total_horas,
                "distribuido": total_fuente, "estado": "LISTA",
            })

        estado = "LISTA" if distribucion else "PENDIENTE"
        hay_aplicadas = any(
            f["estado"] == "APLICADA" for f in fuentes_resumen
        )
        if hay_aplicadas:
            estado = "APLICADA"
        elif any(f["estado"] == "REVERTIDA" for f in fuentes_resumen):
            estado = "REVERTIDA"
        return {
            "periodo": periodo,
            "estado": estado,
            "periodo_abierto": periodo.estado == EstadoPeriodo.ABIERTO,
            "fuentes": fuentes_resumen,
            "distribucion": distribucion,
            "alertas": alertas,
            "total_pool": total_pool,
            "total_distribuido": total_distribuido,
            "puede_aplicar": bool(distribucion),
            "puede_revertir": hay_aplicadas,
        }

    def aplicar(self, actor, periodo_id):
        _verificar(actor)
        vista = self.previsualizar(actor, periodo_id)
        periodo = vista["periodo"]
        if periodo.estado != EstadoPeriodo.ABIERTO:
            raise PeriodoNoAbiertoError(
                "El período contable está cerrado; no se pueden aplicar "
                "costos indirectos."
            )
        if not vista["distribucion"]:
            return vista
        configuracion = self._repo.configuracion(Elemento.INDIRECTO)
        if configuracion is None:
            raise ConfiguracionNoEncontradaError(
                "Configura la cuenta de costos indirectos antes de aplicar "
                "el pool."
            )
        cuenta_costo = configuracion.cuenta_costo
        self._verificar_cuenta_asiento(cuenta_costo)

        try:
            with self._transaccion():
                for linea in vista["distribucion"]:
                    self._registrar_linea(actor, periodo, cuenta_costo,
                                         linea)
        except IntegrityError:
            # El índice único de la clave impide repetir el envío si dos
            # peticiones confirman la misma aplicación simultáneamente.
            return self.previsualizar(actor, periodo_id)

        self._auditar(
            actor, Accion.CARGO_ORDEN,
            f"Indirectos período {periodo.pk}",
            f"Distribuidos ${vista['total_distribuido']:.2f} en "
            f"{len(vista['distribucion'])} órdenes",
        )
        return self.previsualizar(actor, periodo_id)

    def revertir(self, actor, periodo_id):
        _verificar(actor)
        periodo = self._periodo(periodo_id)
        if periodo.estado != EstadoPeriodo.ABIERTO:
            raise PeriodoNoAbiertoError(
                "El período está cerrado; no se puede revertir la "
                "aplicación de indirectos."
            )
        registros = [r for r in self._repo.registros_indirectos_periodo(
            periodo
        ) if r.vigente]
        if not registros:
            return self.previsualizar(actor, periodo_id)

        with self._transaccion():
            for registro in registros:
                lineas = calculos.lineas_contrarias(
                    calculos.lineas_reclasificacion(
                        registro.fuente_indirecta.cuenta_origen,
                        registro.cuenta_costo, registro.importe,
                    )
                )
                clave = f"rev-indirecto-{periodo.pk}-{registro.pk}"
                transaccion = self._mayor.crear_transaccion(usuario=actor)
                if not calculos.cuadra(lineas):
                    raise AsientoDescuadradoError(
                        "El contra-asiento automático no cuadra."
                    )
                for cuenta, importe in lineas:
                    self._mayor.crear_movimiento(
                        transaccion=transaccion, cuenta=cuenta,
                        fecha=periodo.fecha_fin,
                        concepto=(f"Reversión indirectos · "
                                  f"{registro.fuente_indirecta.nombre}"),
                        referencia=(f"OT-{registro.orden_id} · "
                                    f"I{registro.pk}")[:40],
                        tipo=TipoMovimiento.AJUSTE, importe=importe,
                    )
                self._repo.crear_asiento(
                    transaccion=transaccion,
                    tipo=AsientoCosto.TIPO_ANULACION,
                    orden=registro.orden, registro=registro,
                    clave_idempotencia=clave,
                )
                registro.estado = RegistroCosto.ESTADO_ANULADO
                registro.motivo_anulacion = (
                    "Reversión de aplicación de indirectos del período"
                )
                registro.anulado_por = actor
                registro.anulado_en = timezone.now()
                self._repo.guardar_registro(registro)

        self._auditar(
            actor, Accion.CARGO_ORDEN,
            f"Reversión indirectos período {periodo.pk}",
            f"Contra-asientos: {len(registros)}",
        )
        return self.previsualizar(actor, periodo_id)

    def _periodo(self, periodo_id):
        periodo = self._repo.obtener_periodo_contable(periodo_id)
        if periodo is None:
            raise DatosInsuficientesError(
                "Selecciona un período contable válido.", campo="periodo"
            )
        return periodo

    def _verificar_cuenta_asiento(self, cuenta):
        if (cuenta is None or not cuenta.activa
                or self._mayor.tiene_subcuentas(cuenta)):
            raise CuentaNoValidaError(
                "La cuenta de costos indirectos no admite movimientos."
            )

    def _registrar_linea(self, actor, periodo, cuenta_costo, linea):
        fuente = linea["fuente"]
        orden = self._repo.obtener_orden(linea["orden_id"])
        if orden is None or not orden.abierta:
            raise OrdenCerradaError(
                "Una orden dejó de estar abierta; no se aplicó el período."
            )
        if self._repo.cuenta_indirecta_excluida(fuente.cuenta_origen):
            raise CuentaNoValidaError(
                f"La cuenta de «{fuente.nombre}» está excluida."
            )
        self._verificar_cuenta_asiento(fuente.cuenta_origen)
        importe = calculos.a_centavos(linea["importe"])
        clave = f"ind-{periodo.pk}-{fuente.pk}-{orden.pk}"
        if self._repo.registro_por_clave(clave) is not None:
            return

        descripcion = f"Indirecto automático · {fuente.nombre}"
        if fuente.proceso is not None:
            descripcion += f" · {fuente.proceso.nombre}"
        registro = self._repo.crear_registro(
            orden=orden, elemento=Elemento.INDIRECTO,
            fecha=periodo.fecha_fin, proceso=fuente.proceso,
            descripcion=descripcion[:200], horas=linea["horas"],
            costo_hora=None, importe=importe,
            cuenta_costo=cuenta_costo,
            fuente_indirecta=fuente, periodo_indirecto=periodo,
            clave_idempotencia=clave, usuario=actor,
        )
        lineas = calculos.lineas_reclasificacion(
            fuente.cuenta_origen, cuenta_costo, importe
        )
        if not calculos.cuadra(lineas):
            raise AsientoDescuadradoError(
                "El asiento automático de indirectos no cuadra."
            )
        transaccion = self._mayor.crear_transaccion(usuario=actor)
        for cuenta, monto in lineas:
            self._mayor.crear_movimiento(
                transaccion=transaccion, cuenta=cuenta,
                fecha=periodo.fecha_fin,
                concepto=f"OT-{orden.pk} · {descripcion}"[:200],
                referencia=f"OT-{orden.pk} · I{registro.pk}"[:40],
                tipo=TipoMovimiento.DIARIO, importe=monto,
            )
        self._repo.crear_asiento(
            transaccion=transaccion, tipo=AsientoCosto.TIPO_REGISTRO,
            orden=orden, registro=registro, clave_idempotencia=clave,
        )
