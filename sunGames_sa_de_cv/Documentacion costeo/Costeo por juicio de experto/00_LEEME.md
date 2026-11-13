# Costeo por juicio de experto — SunGames, S.A. de C.V.

Procedimiento con el que SunGames estima y aprueba la línea base de cada videojuego antes de abrir su
orden de trabajo. Combina descomposición, analogía, panel Delphi y tres escenarios con fórmula PERT.
El resultado es el presupuesto que después ejecuta el costeo por órdenes de trabajo.

Documentos de uso interno y confidencial.

## Contenido

| # | Archivo | Qué contiene |
|---|---------|--------------|
| 01 | `01_Manual_de_costeo_por_juicio_de_expertos.docx` | Manual SG-CTL-002: objetivo, marco de referencia, definiciones, roles, criterios de aplicación, proceso de ocho pasos, técnicas, fórmulas, tolerancias, criterios de calidad, trazabilidad, controles, caso aplicado y anexos. |
| 02 | `02_Estimacion_SG-TIT-01.xlsx` | Libro de estimación con nueve hojas y fórmulas reales: Portada, Panel, Ronda 1, Ronda 2, Consolidación, PERT, Sensibilidad, Línea base y Soportes. |
| — | `Soportes/` | Diez documentos con membrete y sello de SunGames (SJE-01 a SJE-10). |

## Orden de lectura

1. **Manual (01).** Explica el proceso completo y remite a los soportes.
2. **Libro de estimación (02).** Permite recalcular las rondas, la consolidación, el PERT y la línea
   base. Las celdas amarillas son datos de entrada; el resto son fórmulas.
3. **Soportes.** Se consultan para verificar la evidencia de cada paso.

## Soportes incluidos

| Código | Documento |
|--------|-----------|
| SJE-01 | Ficha del proyecto y alcance |
| SJE-02 | Acta de conformación del panel |
| SJE-03 | Estimación individual — experto 1 |
| SJE-04 | Estimación individual — experto 2 |
| SJE-05 | Estimación individual — experto 3 |
| SJE-06 | Consolidación y rondas Delphi |
| SJE-07 | Cálculo PERT y sensibilidad |
| SJE-08 | Registro de supuestos y riesgos |
| SJE-09 | Base histórica de proyectos |
| SJE-10 | Acta de aprobación de la línea base |

## Cifras de referencia — orden SG-TIT-01 (Aurora Salvaje)

| Concepto | Valor |
|----------|-------|
| Ronda 1 — E1 / E2 / E3 | 4,250 / 3,880 / 4,050 h |
| Ronda 1 — media | 4,060.00 h |
| Ronda 1 — coeficiente de variación | 4.56% |
| Ronda 2 — E1 / E2 / E3 | 4,070 / 3,940 / 3,990 h |
| Ronda 2 — media | 4,000.00 h |
| Ronda 2 — coeficiente de variación | 1.64% |
| PERT — O / M / P | 3,100 / 3,900 / 5,300 h |
| PERT — valor esperado | 4,000.00 h |
| PERT — desviación | 366.67 h |
| Analogía (Nébula × 2.075) | 3,850 h (3.75% bajo la línea base) |
| Mano de obra directa | USD 25,500.00 |
| CIF presupuestados | USD 4,800.00 |
| Línea base total | USD 30,300.00 |
| Tasa predeterminada de CIF | USD 1.20 por hora |

## Composición del panel

| Código | Experto | Perfil |
|--------|---------|--------|
| E1 | Carla Sofía Jiménez | Líder de Desarrollo de Videojuegos (P-007) |
| E2 | Bruno Alberto Estrada | Desarrollador Senior (P-008) |
| E3 | Diego Edgardo González Sánchez | Contador General |
| — | Josué Nehemías Renderos Hernández | Facilitador (no estima) |

## Relación con el otro método

La línea base aprobada en SJE-10 abre la orden SG-TIT-01 y se ejecuta con el procedimiento de
**Costeo por ordenes de trabajo** (manual SG-CTL-001, hoja de costos y soportes SOP-01 a SOP-10). Este
expediente no registra costos reales: solo estima y aprueba el presupuesto.

## Notas

- Las fórmulas del Excel se verificaron con recálculo real: ronda 1 en 4,060.00 h; ronda 2 en
  4,000.00 h; PERT en 4,000.00 h; línea base en USD 30,300.00; tasa en USD 1.20 por hora.
- Fechas en formato dd/mm/aaaa e importes en USD con dos decimales.
