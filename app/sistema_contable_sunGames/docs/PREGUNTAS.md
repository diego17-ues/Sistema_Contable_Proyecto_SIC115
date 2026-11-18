# Preguntas pendientes — Subsistema de Costos

Lo que no se puede resolver con el código se registra aquí. No inventar
reglas: cada punto requiere respuesta antes de implementarse.

## Cuentas contables (bloquean asientos si no se resuelven)

1. **Cuenta de origen de sueldos y prestaciones**: para el asiento de
   mano de obra (debe 4101) ¿cuál es la cuenta del Haber? Candidatas en
   el catálogo: `2106` Sueldos y prestaciones por pagar (pasivo),
   `4201` Sueldos y salarios administrativos o `4202` Prestaciones y
   cargas patronales (gasto). Ninguna está confirmada.

2. **Cuenta de prestaciones y cargas patronales**: para la tasa real de
   cierre (saldo de la cuenta / salarios brutos) ¿qué cuenta es la de
   prestaciones y cargas patronales? Candidata: `2105` Cargas patronales
   por pagar; alternativa `4202`. Confirmar.

3. **Alcance de la cuenta 4102** (Servicios directos de desarrollo):
   ¿qué conceptos capitalizables entran aquí? El encargo dice "servicios
   o licencias directos que la política permita capitalizar" pero la
   política no está definida. Si no hay ninguno, 4102 queda sin
   movimiento — confirmar.

4. **Cuenta de depreciación**: la depreciación aplicada a órdenes
   (debe 4103) necesita su Haber. ¿Es `1203` Depreciación acumulada,
   `4207` Depreciación de mobiliario y equipo, u otra? Confirmar.

5. **Intangible en desarrollo e intangible en uso**: el catálogo no
   tiene cuentas con ese nombre; las candidatas son `1106`
   Videojuegos en desarrollo y `1107` Videojuegos terminados (activo,
   rubro 1). ¿Son esas las cuentas del traslado de cierre y del
   lanzamiento? Confirmar código exacto.

## Mecanismo y modelo

6. **Mecanismo de asientos**: el mayor no tiene entidad "asiento"; el
   precedente multi-cuenta es `ventas` creando `Transaccion` +
   `Movimiento` por repositorio (`libro_mayor/repositories.py:46-55`).
   ¿Se acepta ese patrón para costos (sin modificar contabilidad
   general), o se requiere una API formal de asientos en `libro_mayor`
   (modificación que necesita aprobación explícita)?

7. **Auxiliar por orden de trabajo**: `Movimiento` no tiene campo
   auxiliar/orden; la trazabilidad iría en concepto/referencia (40
   caracteres) + tablas propias de costos. ¿Es suficiente o se requiere
   modificar el modelo del mayor?

8. **Rol de usuario**: en `main` solo existen `ADMINISTRADOR` y
   `CONTADOR_GENERAL`; `CONTADOR_COSTOS` vive en la rama
   `costos/estimacion` sin fusionar. ¿Las órdenes de trabajo las opera
   el Contador General, el Administrador, o se crea el rol
   `CONTADOR_COSTOS` en esta rama también?

9. **Tasa por hora de proceso**: el encargo habla de "costo del proceso
   en el período / horas base". ¿De dónde sale ese costo real? ¿Se
   captura manual por período/proceso, o debe calcularse desde cuentas
   de gasto ya registradas en el mayor? En corte provisional se permite
   tasa presupuestada — ¿dónde se define esa tasa?

10. **Salario de referencia para mano de obra**: la tabla equivalente
    está en la app `estimacion` (prohibido depender de ella). ¿Se crea
    una tabla propia en el módulo de costos con la misma estructura
    (rol/nivel, salario bruto, vigencia)?

11. **Período contable faltante**: `periodo_de(fecha)` exige un
    `PeriodoContable` que cubra la fecha del cargo. Si una orden registra
    horas/cargos en fechas sin período, el asiento fallará. ¿Se crean
    períodos por adelantado o el módulo debe rechazar con mensaje
    claro?

12. **Servicios de terceros**: "el fondo compartido se reparte entre
    órdenes por horas de desarrollo". ¿"Horas de desarrollo" = suma de
    horas registradas en la orden (RegistroHora) o una cifra aparte?
    Confirmar la base del prorrateo.

13. **Depreciación de equipo (O5)**: ¿el registro de equipos y el cálculo
    de depreciación los captura el módulo de costos (costo, vida útil,
    valor residual, tipo de uso) o ya existe un registro en contabilidad
    general del que solo se toma la tasa? El catálogo tiene `1201`,
    `1202`, `1203` pero no un módulo de activos fijos.
