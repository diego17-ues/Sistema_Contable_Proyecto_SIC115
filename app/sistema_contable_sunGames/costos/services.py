"""Servicios del subsistema de costos (órdenes de trabajo, Etapa 1).

Reglas:
- Cada registro de costo genera un asiento cuadrado en el Libro Mayor
  mediante el repositorio de la contabilidad general (nunca se escribe
  directo en sus tablas). Debe a la cuenta de costo del elemento y haber
  a la contrapartida configurada.
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
from libro_mayor.models import TipoMovimiento
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
from .models import AsientoCosto, Elemento, RegistroCosto

ROLES_COSTOS = frozenset({
    Rol.ADMINISTRADOR, Rol.CONTADOR_GENERAL, "CONTADOR_COSTOS",
})


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


class OrdenService(CostosService):
    """Alta y consulta de órdenes de trabajo."""

    def listar(self, actor, *, estado=None):
        _verificar(actor)
        return list(self._repo.ordenes(estado=estado))

    def detalle(self, actor, orden_id):
        _verificar(actor)
        return self._orden(orden_id)

    def registros(self, actor, orden):
        _verificar(actor)
        return list(self._repo.registros_de_orden(orden))

    def crear_orden(self, actor, *, nombre_juego, fecha_inicio):
        _verificar(actor)
        nombre = (nombre_juego or "").strip()
        if not nombre:
            raise DatosInsuficientesError(
                "Indica el juego de la orden.", campo="nombre_juego"
            )
        if fecha_inicio is None:
            raise DatosInsuficientesError(
                "Indica la fecha de inicio.", campo="fecha_inicio"
            )
        with self._transaccion():
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
            )
            self._auditar(actor, Accion.ORDEN_TRABAJO,
                          f"OT {orden.pk} · {juego.nombre}", "Alta de orden")
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
                            horas, costo_hora, contrapartida_id, clave):
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
        return self._registrar(
            actor, elemento=Elemento.MANO_OBRA, orden_id=orden_id,
            fecha=fecha, proceso=proceso,
            descripcion=f"Mano de obra · {proceso.nombre}",
            importe=calculos.importe_mano_obra(horas, costo_hora),
            contrapartida_id=contrapartida_id, clave=clave,
            horas=horas, costo_hora=costo_hora,
        )

    def registrar_costo(self, actor, *, elemento, orden_id, fecha,
                        proceso_id, descripcion, importe, contrapartida_id,
                        clave):
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
        importe = Decimal(importe or 0)
        if importe <= 0:
            raise DatosInsuficientesError(
                "El monto debe ser mayor que cero.", campo="importe"
            )
        return self._registrar(
            actor, elemento=elemento, orden_id=orden_id, fecha=fecha,
            proceso=proceso, descripcion=descripcion,
            importe=calculos.a_centavos(importe),
            contrapartida_id=contrapartida_id, clave=clave,
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
        motivo = (motivo or "").strip()
        if not motivo:
            raise DatosInsuficientesError(
                "Indica el motivo de la anulación.", campo="motivo"
            )
        fecha = self._hoy()
        self._verificar_periodo(fecha)
        lineas = self._lineas_anulacion(registro)
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
                   descripcion, importe, contrapartida_id, clave,
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
        contrapartida = self._contrapartida(config, contrapartida_id)
        lineas = calculos.lineas_registro(cuenta_costo, contrapartida,
                                          importe)
        try:
            with self._transaccion():
                registro = self._repo.crear_registro(
                    orden=orden, elemento=elemento, fecha=fecha,
                    proceso=proceso, descripcion=descripcion[:200],
                    horas=horas, costo_hora=costo_hora, importe=importe,
                    cuenta_costo=cuenta_costo, contrapartida=contrapartida,
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
        if not calculos.cuadra(lineas):
            raise AsientoDescuadradoError("El asiento no cuadra.")
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
        return calculos.lineas_contrarias(calculos.lineas_registro(
            registro.cuenta_costo, registro.contrapartida, registro.importe
        ))

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

    def _contrapartida(self, config, contrapartida_id):
        permitidas = {c.pk: c for c in config.contrapartidas.all()}
        if not contrapartida_id:
            contrapartida_id = config.contrapartida_defecto_id
        cuenta = permitidas.get(int(contrapartida_id))
        if cuenta is None:
            raise CuentaNoValidaError(
                "La contrapartida no está permitida para este elemento.",
                campo="contrapartida",
            )
        return self._cuenta_valida(cuenta)


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

    def guardar_configuracion(self, actor, *, elemento, cuenta_costo,
                              contrapartidas, contrapartida_defecto):
        _verificar(actor)
        if elemento not in Elemento.values:
            raise DatosInsuficientesError("Elemento del costo no válido.")
        contrapartidas = list(contrapartidas)
        if not contrapartidas:
            raise DatosInsuficientesError(
                "Selecciona al menos una contrapartida.",
                campo="contrapartidas",
            )
        if contrapartida_defecto not in contrapartidas:
            raise CuentaNoValidaError(
                "La contrapartida por defecto debe estar entre las "
                "permitidas.", campo="contrapartida_defecto",
            )
        if cuenta_costo in contrapartidas:
            raise CuentaNoValidaError(
                "La cuenta de costo no puede ser su propia contrapartida.",
                campo="contrapartidas",
            )
        with self._transaccion():
            config = self._repo.guardar_configuracion(
                elemento=elemento, cuenta_costo=cuenta_costo,
                contrapartidas=contrapartidas,
                contrapartida_defecto=contrapartida_defecto,
            )
            self._auditar(
                actor, Accion.CATALOGO_COSTOS,
                f"Cuentas {Elemento(elemento).label}",
                f"Debe {cuenta_costo.codigo} · haber "
                + ", ".join(c.codigo for c in contrapartidas),
            )
        return config
