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
