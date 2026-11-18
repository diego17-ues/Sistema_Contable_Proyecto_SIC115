# R0 — Diagnóstico y plan de reestructuración del módulo de costos

Rama de trabajo: `main` (la rama `costos/ordenes-trabajo` ya fue
fusionada a `main`; se continúa sobre `main` por instrucción del
usuario). Fecha: 2026-11-18.

## 1. Contabilidad general (confirmado en código)

- **Asientos**: no existe entidad "asiento" ni validación de partida
  doble. El mayor es `Transaccion` + `Movimiento` (importe firmado:
  positivo = Debe, negativo = Haber), con `tipo`, `concepto` (≤200) y
  `referencia` (≤40). El mecanismo reutilizable sin tocar la contabilidad
  general es `libro_mayor.repositories.TransaccionRepository`
  (`crear_transaccion`, `crear_movimiento`, `obtener_cuenta`,
  `tiene_subcuentas`, `periodo_de`), patrón demostrado en
  `ventas.services.contabilizar` (`ventas/services.py:222-261`): una
  transacción atómica, validación de cuenta registrable, idempotencia
  por enlace (`venta.transaccion_id`) y bitácora. El cuadre debe=haber
  lo debe garantizar el módulo de costos antes de enviar (nadie lo
  valida).
- **Auxiliar por orden**: `Movimiento` no tiene campo auxiliar. La
  trazabilidad orden/asiento se lleva en `referencia`/`concepto` y en
  tablas propias del módulo (`CargoOrden.transaccion`,
  `AsientoCosto`/`clave_idempotencia`).
- **Períodos**: `PeriodoContable` con `EstadoPeriodo` = `ABIERTO` /
  `CIERRE_PROVISIONAL` (`libro_mayor/models.py:22-26`); `cerrado` es
  cualquier estado ≠ ABIERTO. `Movimiento.save` rechaza fechas en
  período cerrado; `periodo_de(fecha)` falla si ningún período cubre la
  fecha (debe crearse el período desde Estados financieros).
- **Cierre y reapertura**: `CierrePeriodoService` cierra provisional o
  anual emitiendo snapshots inmutables; `reabrir` es solo
  Administrador + contraseña (`estados_financieros/services.py:315`).
  La reapertura cambia el estado del período pero **no revierte
  movimientos**: los traslados de costos a 1106 deben revertirse con
  asientos inversos propios del módulo (ver PREGUNTAS).
- **Activos y depreciación**: la contabilidad general **no calcula ni
  registra depreciación automáticamente**; solo existen las cuentas
  (1201, 1202, 1203, 1207 no; 4207 Depreciación de mobiliario, 4208
  Amortización de licencias). El módulo leerá indirectos del saldo de
  las cuentas mapeadas en el período; no calcula la depreciación.
- **Planilla**: no hay empleados, departamentos ni nómina. No existe
  costo por hora real por empleado → se conserva `TarifaProceso`
  propia (registrado en PREGUNTAS como pendiente de revisión).
- **Catálogo real** (verificado en BD): existen 1106 Videojuegos en
  desarrollo, 1107 Videojuegos terminados, 1108 Amortización acumulada
  de videojuegos, 1201/1202 equipos, 1203 Depreciación acumulada,
  1204 Licencias de software, 1205 Amort. acum. licencias, 2105 Cargas
  patronales por pagar, 2106 Sueldos y prestaciones por pagar,
  4101–4104, 4201–4208 (incluye 4203 Honorarios profesionales),
  4301–4503. Todo lo que el asiento necesita es seleccionable por
  `MapeoCuenta`; si el mapeo o la cuenta no existe o está inactiva, el
  asiento queda bloqueado.

## 2. Qué se elimina (R1)

Modelos y todo su rastro en servicios, formularios, vistas, URLs,
templates, seed y pruebas:

- `SalarioReferencia` (tabuladores) — lo sustituye `TarifaProceso`.
- `FondoCompartido` y su prorrateo.
- `Equipo` y `UsoEquipo` (horas máquina) — la depreciación vive en la
  contabilidad general; costos solo lee las cuentas mapeadas.
- `CorteCostos` y `CorteDetalle` (pestaña y pantallas de cortes).
- Origen `SERVICIO_ASIGNADO` y campo `afecta_mayor`: los servicios
  profesionales son gasto del período (4203/4502) y no entran a la
  orden. Desaparece el "costo de gestión" y la conciliación.
- Ajustes de sobre/subaplicación (`ORIGEN_AJUSTE` por diferencia de
  tasa): la tasa se calcula con el costo real del período, ya no hay
  diferencia.
- `CostoProceso` (costo capturado a mano): el costo indirecto real se
  lee del mayor por cuenta origen mapeada.
- Parámetros `horas_semana`, `semanas_año`, `tasa_cargas_patronales`:
  el costo por hora viene de `TarifaProceso`, no de una fórmula.

## 3. Qué se conserva

- `Juego`, `OrdenTrabajo` (con `capitalizable_desde`, estado,
  `fecha_cierre`), `Proceso` (ahora catálogo de 5 procesos),
  `RegistroHora`, `CargoOrden` (simplificado), `ParametroVigente`,
  `MapeoCuenta` (ampliado), arquitectura vista→form→servicio→repo→modelo,
  inyección por `composition.py`, bitácora, excepciones de dominio,
  `repartir` (centavos a la última orden), cálculos en `Decimal`,
  pantallas y menú "Costeo Videojuego".
- Regla de capitalización: con `capitalizable_desde` vacío se capitaliza
  **todo** (cambio respecto de la versión anterior, donde vacío = nada);
  cargos anteriores a la fecha quedan como gasto del período, fuera de
  la serie 41.

## 4. Qué se crea / cambia

- `Proceso`: catálogo configurable, semilla inicial Diseño,
  Programación, Arte, Audio y QA (marcada "a confirmar").
- `TarifaProceso` (nuevo): costo por hora pagada por proceso con
  vigencia; editable solo por Contador de Costos; incluye prestaciones
  según política (sin desglose).
- `MapeoCuenta` (ampliado): proceso (opcional), elemento del costo
  (mano_obra | directo | indirecto), cuenta **origen** del catálogo,
  cuenta **destino** (4101/4102/4103 según elemento), porcentaje.
  Las cuentas indirectas sin proceso asignado se reparten por horas
  totales del período.
- `OrdenTrabajo` (campos nuevos): `licencias_estimadas` (entero > 0,
  editable), `estimacion_ref` (FK opcional, solo lectura, a la versión
  de presupuesto aprobada de `estimacion`; solo muestra el total
  estimado, sin variaciones).
- `AsientoCosto` (nuevo, o campos en `CargoOrden`): transacción del
  mayor, tipo (mano_obra | directo | indirecto | traslado_cierre |
  cierre_orden | amortizacion | reversion), orden, período,
  clave_idempotencia. Garantiza origen + idempotencia por prueba 10.
- `ParametroVigente`: `vida_util_anios`=4 (**VERIFICAR**),
  `base_dias_anio`=365, `valor_residual`=0.
- `AmortizacionOrden` (nuevo): cargo anual/mensual/diario por período
  cerrado, acumulado, valor en libros, fin de vida útil; idempotente
  por orden + período.
- Servicios: `registrar_hora` emite asiento 1 (debe 4101 / haber cuenta
  origen mapeada); `registrar_cargo` (directo) emite asiento 2 (4102 /
  origen); `aplicar_indirectos` lee saldos del mayor por cuenta origen
  mapeada → tasa por proceso → asiento 3 (4103 / orígenes) con
  anti doble conteo; `cerrar_periodo_costos` emite asiento 4 (1106 /
  4101-4103 por orden) y 6 (4104 / 1108 por orden cerrada);
  `cerrar_orden` emite asiento 5 en una transacción (traslado 41→1106
  + 1106→1107). Todos cuadran antes de enviarse.
- Interfaz: se mantiene el aspecto aprobado; detalle de orden con
  resumen por 3 elementos + costo total, licencias estimadas y costo
  unitario (4 decimales de cálculo, 2 de vista, "—" si falta), sección
  "Dónde está el costo", pestañas Cargos/Horas/Asientos/Amortización
  (esta última solo cerrada); nueva pantalla de cierre de período con
  vista previa debe/haber.

## 5. Riesgos y bloqueos identificados

- Sin cuenta origen mapeada, el tipo de asiento queda bloqueado (no se
  inventan códigos). Confirmados en catálogo: 4101–4104, 1106–1108.
- La "depreciación de la contabilidad general" no existe aún: los
  indirectos se leen del saldo de la cuenta mapeada (p. ej. 4207) en el
  período; si nadie registra ese gasto, el pool es cero y solo alerta.
- Reapertura de período: el mayor la permite (Admin) pero no revierte
  movimientos; el módulo necesita una acción propia de reversión o un
  punto de llamada en estados_financieros (modificación que requiere
  aprobación → PREGUNTAS).
- `periodo_de` exige que exista `PeriodoContable` cubriendo la fecha;
  el módulo no crea períodos (los crea el cierre de estados
  financieros).
