# Costeo por órdenes de trabajo — SunGames, S.A. de C.V.

Procedimiento con el que SunGames acumula el costo real de cada videojuego desde que se abre la
orden hasta que el título se termina, se traslada al activo y se amortiza. Toma como punto de partida
la línea base aprobada por juicio de experto.

Documentos de uso interno y confidencial.

## Contenido

| # | Archivo | Qué contiene |
|---|---------|--------------|
| 01 | `01_Manual_de_costeo_por_ordenes_de_trabajo.docx` | Manual SG-CTL-001: objetivo, marco normativo, definiciones, objeto de costo, cuentas, fórmulas, proceso de doce pasos, estados de la orden, asientos tipo, parámetros, controles, trazabilidad, reportes y caso aplicado. |
| 02 | `02_Ordenes_de_trabajo_v2.docx` | Documento SG-CTL-004, versión 2.0 de las órdenes de trabajo: fundamento metodológico, decisiones de armonización de cuentas, roles, tasa por período, RF-077, soportes y vida útil del título. |
| 03 | `03_Hoja_de_costos_SG-TIT-01.xlsx` | Hoja de costos con ocho hojas y fórmulas reales: Portada, Presupuesto, Tarifas, Horas, CIF, Resumen, Asientos y Soportes. |
| — | `Soportes/` | Diez documentos con membrete y sello de SunGames (SOP-01 a SOP-10). |

## Orden de lectura

1. **Manual (01).** Explica el modelo completo y remite a los demás documentos.
2. **v2 (02).** Justifica las decisiones, la armonización de cuentas y la trazabilidad con la
   especificación.
3. **Hoja de costos (03).** Muestra las cifras en operación. Las celdas amarillas son datos de
   entrada; el resto son fórmulas.
4. **Soportes.** Se consultan cuando se necesita la evidencia de una cifra concreta.

## Soportes incluidos

| Código | Documento |
|--------|-----------|
| SOP-01 | Planilla del equipo de desarrollo — marzo 2026 |
| SOP-02 | Hoja de tiempo aprobada — marzo 2026 |
| SOP-03 | Tabla de tarifas vigentes 2026 |
| SOP-04 | Factura FAC-2026-0102 — licencia de motor gráfico |
| SOP-05 | Factura FAC-2026-0468 — servidores y hosting |
| SOP-06 | Cálculo de depreciación del equipo de producción |
| SOP-07 | Factura FAC-2026-0417 — servicios profesionales (voces) |
| SOP-08 | Comprobante de retención de renta |
| SOP-09 | Presupuesto aprobado SG-TIT-01 |
| SOP-10 | Conciliación de horas con planilla |

## Trazabilidad valor → documento

| Valor | Soporte |
|-------|---------|
| Presupuesto y tasa predeterminada | SOP-09 |
| Horas aprobadas por programador | SOP-02 |
| Tarifas vigentes | SOP-03 |
| Costo de mano de obra y planilla | SOP-01 |
| CIF por licencia de motor (180.00) | SOP-04 |
| CIF por servidores (120.00) | SOP-05 |
| CIF por depreciación (110.00) | SOP-06 |
| Servicio profesional de terceros (1,000.00, excluido) | SOP-07 |
| Retención del 10% (100.00) | SOP-08 |
| Conciliación de horas | SOP-10 |

## Cifras de referencia — orden SG-TIT-01 (marzo de 2026)

| Concepto | Importe |
|----------|---------|
| Presupuesto total de la orden | USD 30,300.00 |
| Mano de obra presupuestada (4,000 h) | USD 25,500.00 |
| CIF presupuestados | USD 4,800.00 |
| Tasa predeterminada | USD 1.20 por hora |
| Horas reales de marzo | 330.00 h |
| Mano de obra real de marzo | USD 2,160.00 |
| CIF aplicado | USD 396.00 |
| CIF real | USD 410.00 |
| Subaplicación | USD 14.00 |
| Costo trasladado a 1106 | USD 2,556.00 |
| Variación total de MOD al cierre (programador B) | USD 1,000.00 (horas 600.00 + tarifa 400.00) |

## Relación con el otro método

La línea base de 4,000 horas y USD 30,300.00 proviene del expediente de **Costeo por juicio de
experto** (manual SG-CTL-002 y soportes SJE-01 a SJE-10). Este procedimiento no la recalcula: la
recibe aprobada y la usa como punto de comparación de las variaciones.

## Notas

- Las cuentas siguen el Anexo 3 del Manual de aplicación del catálogo de cuentas.
- Las fórmulas del Excel se verificaron con recálculo real: presupuesto 30,300.00; MOD real
  2,160.00; CIF aplicado 396.00; costo acumulado 2,556.00; asientos cuadrados en 5,126.00.
- Fechas en formato dd/mm/aaaa e importes en USD con dos decimales.
