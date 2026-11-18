# Avance — Subsistema de Costos (Órdenes de Trabajo)

Rama: `costos/ordenes-trabajo` (desde `main`).
Fecha: 2026-11-18.

## Fase O0 — Diagnóstico (commit `fc543cf`)

- `docs/DIAGNOSTICO_OT.md`: mecanismo del mayor (Transaccion + Movimiento
  firmado, sin entidad "asiento" ni cuadre obligatorio), períodos,
  catálogo de cuentas, roles, bitácora e interfaz.
- `docs/PREGUNTAS.md`: 13 puntos abiertos (cuentas de origen, rol,
  auxiliar por orden, etc.).

## Implementación del módulo funcional (sin asientos contables)

Decisión del usuario: usar las cuentas ya definidas en el catálogo;
los costos capitalizables quedan en la serie 41 mientras el período
está abierto y se trasladan a **Videojuegos terminados (1107)** al
cierre/corte. **No hay registros contables todavía**: los cargos se
guardan en tablas propias del módulo con cuenta destino (snapshot),
clave de idempotencia y `referencia_asiento` preparada para la fase de
asientos. Depreciación línea recta automática por equipo.

### App `costos`

- **Modelos**: `Juego`, `OrdenTrabajo` (una por juego, `capitalizable_desde`),
  `Proceso`, `CostoProceso` (costo real + horas base + tasa presupuestada
  por período), `ParametroVigente`, `SalarioReferencia`, `MapeoCuenta`
  (concepto → cuenta real del catálogo), `RegistroHora`, `CargoOrden`
  (origen, afecta_mayor, cuenta snapshot, clave_idempotencia única,
  referencia_asiento, corte/traslado_intangible), `FondoCompartido`,
  `Equipo`, `UsoEquipo`, `CorteCostos` + `CorteDetalle`.
- **Cálculos puros** (`calculos.py`, todo Decimal): horas mensuales
  (44×52/12 = 190.6667), costo/hora pagada (salario×(1+tasa)/horas_mes),
  tasa de proceso, cuota de depreciación línea recta y `repartir`
  (centavos al último).
- **Servicios**: `OrdenService` (órdenes, horas → cargo 4101 automático,
  cargos manuales, cierre con CONFIRMAR), `CalculoService` (tasas por
  proceso + ajuste de diferencia por horas, distribución de fondos una
  sola vez, depreciación mensual por tipo de uso, cortes
  provisional/definitivo y reversión), `CatalogoCostosService`.
- **Semilla** (`0002`): 4 procesos, mapeos 4101/4102/4103/1107,
  parámetros horas_semana=44, semanas_año=52,
  tasa_cargas_patronales=0.246 (**verificado=False → VERIFICAR**).
- **Acceso**: módulo `costos` en `AccesoService` para Contador General y
  Administrador; entrada en el menú (app.js) y `SCREEN_URL_NAMES`.
- **Bitácora**: 6 acciones nuevas (`ORDEN_TRABAJO`, `CARGO_ORDEN`,
  `FONDO_COMPARTIDO`, `EQUIPO_COSTOS`, `CORTE_COSTOS`,
  `CATALOGO_COSTOS`) + migración `bitacora.0009`.
- **Pantallas** (templates del servidor, mismo layout/tokens):
  - `/panel/costos/` lista de órdenes con filtros y paginación.
  - `/panel/costos/<id>/` detalle con resumen (en 41, en corte,
    intangible, gasto del período, costo contable y de gestión) y
    pestañas Cargos / Horas / Cortes; modales de horas, cargo directo y
    cierre.
  - `/panel/costos/catalogos/` procesos, costos de proceso por período,
    aplicación de tasas, parámetros, salarios, mapeo de cuentas,
    fondos compartidos, equipos/usos, depreciación y cortes.

### Reglas implementadas

- Período cerrado u orden cerrada rechazan cargos/horas nuevos.
- `capitalizable_desde` vacío → nada capitaliza + alerta en pantalla.
- Cargos anteriores a la fecha quedan como gasto del período.
- `afecta_mayor=False` → sin cuenta, no capitaliza, suma al costo de
  gestión (servicios de terceros).
- Tasas de proceso: costo del período ÷ horas base; ajuste de
  sobre/subaplicación repartido por horas del proceso. Idempotente por
  `clave_idempotencia`.
- Fondos: reparto por horas de desarrollo con ajuste de centavos en la
  última orden; una sola distribución.
- Depreciación: exclusivo → cuota completa a su orden; compartido →
  cuota/horas_mes × horas máquina registradas (capacidad ociosa fuera);
  administración/ocioso → sin cargo.
- Corte provisional: marca cargos con corte vigente (salen de la 41,
  reversibles); definitivo: `traslado_intangible` permanente. Nada toca
  el Libro Mayor.

### Pruebas

- `manage.py test costos` → **22 pruebas OK** (valores exactos del
  encargo: tasas 60/50/60, A=71,000 B=31,000 total 102,000; ajuste
  2,000/1,000; fondo 4,545.45/2,727.27/1,818.18/909.10; hora 7.8420;
  idempotencia; período/orden cerrados; capitalización por fecha;
  corte provisional + reversión; equipo ocioso/admin sin cargos).
- `manage.py test usuarios costos` → **94 pruebas OK**.

## Pendientes / diferencias con el encargo original

- **Sin asientos contables** (decisión del usuario): la fase de
  integración al mayor queda pendiente; `referencia_asiento` y
  `clave_idempotencia` ya están en el modelo.
- El auxiliar por orden de trabajo no existe en `Movimiento`; cuando se
  hagan los asientos habrá que decidir cómo llevarlo (concepto/
  referencia o propuesta de interfaz).
- Rol de costos: se usó Contador General + Administrador (no existe
  `CONTADOR_COSTOS` en `main`).
- Cuadre debe=haber y "todo asiento cuadra" no aplica aún (no hay
  asientos); se exigirá en la fase de integración.
- Prueba #13 (no leer/escribir estimación): se cumple por diseño — la
  app `costos` no importa nada de `estimacion`.

# Avance — Subsistema de Costos / Módulo de Estimación

Rama: `costos/estimacion`. Fecha: 2026-11-18.

## Hecho

- **Fase 0 — Diagnóstico** (`docs/DIAGNOSTICO_ESTIMACION.md`): stack,
  ejecución de pruebas y estado base documentados.
- **E1 — Modelos y parámetros**: app `estimacion` con `Rol`,
  `SalarioReferencia`, `ParametroVigente`, `Juego`, `FaseEstimacion`,
  `Experto`, `EstimacionExperto`, `RondaDelphi`, `VersionPresupuesto`,
  `LineaPresupuesto`, `CostoDirectoEstimado` y `CostoIndirectoEstimado`.
  Migraciones `0001` y `0002` (datos semilla de los cinco parámetros con
  vigencia; `tasa_cargas_patronales` y `umbral_dispersion_delphi` quedan
  `verificado=False` por estar pendientes de revisión). Pruebas de
  validación de restricciones.
- **E2 — Cálculo puro** (`estimacion/calculos.py`): `horas_mensuales`,
  `costo_hora_pagada`, `tarifa_efectiva`, `tarifa_rol`, `pert` y
  `costo_mano_obra`, todo en `Decimal`. Pruebas con los valores exactos
  del encargo (190.6667; 7.8420; 9.2258; 7.8420 con eficiencia 1.00;
  PERT 533.3333/66.6667; costo 4,920.45 ±0.05).
- **E3 — Delphi**: `EstimacionService` con registro de estimaciones PERT
  por experto/fase/rol/ronda, consolidación (media, mediana y coeficiente
  de variación sobre las horas E de cada experto), umbral desde
  `ParametroVigente`, cierre de ronda con aprobación registrada
  (`RondaDelphi.aprobada_por`, bitácora `CIERRE_RONDA_DELPHI`) y marca de
  fase para nueva ronda cuando el CV supera el umbral. Una ronda cerrada
  no admite estimaciones ni se vuelve a cerrar. Se agregaron acciones de
  bitácora (`ALTA_JUEGO`, `REGISTRO_ESTIMACION`, `CIERRE_RONDA_DELPHI`,
  `GENERACION_PRESUPUESTO`, `APROBACION_PRESUPUESTO`) con su migración.
- **E4 — Presupuesto**: `PresupuestoService.generar_version` toma la
  última ronda cerrada, consolida, calcula tarifa efectiva por rol con el
  salario vigente en la fecha de la versión, crea `VersionPresupuesto` en
  borrador + líneas + costos directos/indirectos y guarda
  `snapshot_parametros` (parámetros, salarios usados y fecha). Versión
  aprobada/vigente inmutable (guardia en el modelo y en el servicio);
  correcciones crean la versión siguiente. `aprobar` y `marcar_vigente`
  (una sola vigente por juego). Sin salario vigente → no se genera y se
  registra alerta `RECHAZADO` en bitácora.
- **Rol y acceso**: `CONTADOR_COSTOS` agregado a `Rol`; el Administrador
  lo registra desde el alta de usuarios existente. `AccesoService`:
  Contador de Costos ve solo `estimacion` (área inicial `estimacion`),
  Administrador ve todo incluida `estimacion`, Contador General no ve el
  módulo. Pantallas renderizadas en servidor (`estimacion.html`,
  `estimacion_juego.html`, `estimacion_catalogos.html`) con el mismo
  estilo y modales de usuarios/catálogo; navegación «Costos → Estimación»
  en `app.js`.
- **Verificación manual**: flujo completo probado con el servidor local
  (alta de juego, estimación, consolidación, cierre de ronda, versión,
  aprobación y vigencia). Datos de prueba eliminados después.

## Pruebas

`python manage.py test estimacion usuarios` → **111 pruebas OK**
(38 del módulo de estimación, resto de usuarios).
Suite completa: **281 pruebas, 52 errores**, idénticos a los 52 errores
preexistentes de `main` (incompatibilidad Django 4.2 / Python 3.14 en el
instrumentado de plantillas del cliente de pruebas). No se introdujeron
errores nuevos ni se modificó código existente fuera del módulo y del
punto de acceso por rol.

## Decisiones tomadas (pendientes de confirmación en PREGUNTAS.md)

- CV = desviación estándar poblacional / media, sobre las horas E PERT
  de cada experto.
- Línea de presupuesto: PERT sobre las medias de O, M y P por fase/rol;
  `horas_E` y `sigma` resultantes; `costo = horas_E × tarifa_efectiva`.
- "Alerta" por falta de salario = registro `RECHAZADO` en bitácora.
- Fases del juego: fijas de SunGames (`estimacion/fases.py`, matriz de
  funciones entregada por el usuario, ajustada: se excluyen «Publicación
  y marketing» y «Finanzas, legal y administración» por ser gasto del
  período). Al alta del juego se crean las 7 fases en orden con su
  clasificación contable (CAPEX/OPEX/MIXTO,
  `FaseEstimacion.clasificacion`, migración 0003). Ya no se capturan a
  mano; la clasificación se muestra en la consolidación y en el detalle
  de cada versión. Los juegos creados antes conservan sus fases
  originales (sin clasificación propia → OPEX por defecto).
- Parámetros y salarios se administran desde la pantalla «Parámetros y
  catálogos» del propio módulo, disponible para Administrador y
  Contador de Costos.
- Las vigencias de un mismo parámetro/salario no pueden traslaparse.
- Eficiencia se aplica como parámetro global `eficiencia` (la edición
  por departamento queda pendiente, ver PREGUNTAS.md).
- Captura Delphi: una sola ronda (ronda 1). El formulario registra una
  matriz PERT por experto y rol que cubre las 7 fases a la vez
  (`registrar_estimacion_matriz`); no se selecciona fase ni ronda.
  Duplicado experto+rol+ronda → `EstimacionDuplicadaError`.
- Costos de fabricación: `CostoFabricacion` por juego (directo e
  indirecto: materiales, máquinas, equipo) capturado desde la ficha del
  juego; `generar_version` los copia a los costos directos/indirectos
  de la versión, por lo que entran al total junto a la mano de obra.
- Versiones: nuevo estado `RECHAZADO` (borrador → rechazado, inmutable;
  permite generar una versión nueva). Bitácora `RECHAZO_PRESUPUESTO` y
  `REGISTRO_COSTO_FABRICACION`.

## Pendiente

- E5 (comparación estimado vs. real): solo se redactó la propuesta en
  `docs/PROPUESTA_COMPARACION.md`; no implementado.
- Costeo real por órdenes de trabajo: fuera de esta sesión.
- Definiciones abiertas en `docs/PREGUNTAS.md`.
