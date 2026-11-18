# Propuesta — Comparación estimado vs. real (E5, no implementado)

Este documento solo define la interfaz de entrada y salida de la fase E5.
No hay código: el costeo real por órdenes de trabajo aún no existe.

## Objetivo

Comparar, por juego/fase/rol, lo estimado en la versión de presupuesto
vigente contra lo real registrado por el costeo por órdenes de trabajo,
descomponiendo la variación en precio (tarifa) y cantidad (horas).

## Entrada

- `VersionPresupuesto` vigente del juego (líneas con `horas_E`, `sigma`,
  `tarifa`, `costo_mano_obra`).
- Costos reales por orden de trabajo (futuro módulo): para cada
  combinación fase/rol, `horas_reales` y `tarifa_real` (costo real de mano
  de obra ÷ horas reales).

## Salida (por fase y rol)

```
variacion_tas = (tarifa_real − tarifa_estimada) × horas_reales
variacion_cant = (horas_reales − horas_estimadas) × tarifa_estimada
variacion_total = variacion_tas + variacion_cant
                 = horas_reales × tarifa_real − horas_estimadas × tarifa_estimada
```

Identidad de descomposición:

```
real − estimado = (tarifa_real − tarifa_est) × horas_reales
                + (horas_reales − horas_est) × tarifa_est
```

## Notas

- `horas_estimadas` = `horas_E` de la línea; `tarifa_estimada` = `tarifa`
  de la línea; `costo estimado` = `horas_E × tarifa`.
- `horas_reales` y `tarifa_real` provendrán del costeo real; si una fase
  no tiene costo real, la variación se reporta como «sin dato» y no como
  cero.
- La dispersión estimada (`sigma`, y la desviación del juego
  `√Σσ²`) sirve para evaluar si la variación total cae dentro del rango
  esperado.
- Todo en `Decimal`; importes en USD con dos decimales.
