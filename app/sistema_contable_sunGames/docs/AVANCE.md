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

`python manage.py test estimacion usuarios` → **106 pruebas OK**
(33 del módulo de estimación, resto de usuarios).
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
  funciones entregada por el usuario). Al alta del juego se crean las 9
  fases en orden con su clasificación contable (CAPEX/OPEX/MIXTO,
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

## Pendiente

- E5 (comparación estimado vs. real): solo se redactó la propuesta en
  `docs/PROPUESTA_COMPARACION.md`; no implementado.
- Costeo real por órdenes de trabajo: fuera de esta sesión.
- Definiciones abiertas en `docs/PREGUNTAS.md`.
