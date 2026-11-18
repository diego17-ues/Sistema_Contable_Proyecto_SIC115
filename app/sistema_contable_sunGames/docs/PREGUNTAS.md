# Preguntas pendientes — Subsistema de Costos

## Resueltas en la implementación actual

- **Cuentas de la serie 41 e intangible**: se usan las cuentas del
  catálogo real vía `MapeoCuenta` (semilla: mano_obra→4101,
  servicio_directo→4102, indirecto→4103, intangible→1107
  "Videojuegos terminados"). Si una cuenta falta o está inactiva, el
  tipo de cargo queda bloqueado con error de dominio.
- **Cuentas de origen de sueldos/prestaciones/depreciación y "intangible
  en desarrollo/uso"**: pendientes solo para la fase de ASIENTOS
  (haber de cada movimiento). Los cargos ya guardan su cuenta destino;
  el origen del gasto se definirá con `docs/PROPUESTA_INTERFAZ.md` o
  respuesta explícita antes de generar movimientos.
- **Asientos contables**: pospuestos por decisión del usuario ("por
  ahora no hay registros contables"). El módulo no escribe en el Libro
  Mayor; `CargoOrden.referencia_asiento` y `clave_idempotencia` quedan
  listos para la integración.

## Abiertas

1. **Mecanismo de asientos**: ¿se acepta el patrón de `ventas`
   (`Transaccion` + `Movimiento` por repositorio, cuadre validado por
   el módulo de costos) o se requiere una API formal en `libro_mayor`
   (modificación que necesita aprobación)?

2. **Auxiliar por orden de trabajo**: `Movimiento` no tiene campo
   auxiliar; la trazabilidad por orden iría en concepto/referencia +
   tablas de costos. ¿Suficiente o se modifica el mayor?

3. **Rol de usuario**: hoy el módulo lo ven Contador General y
   Administrador. ¿Se crea el rol `CONTADOR_COSTOS` en esta rama o se
   mantiene así?

4. **Cuenta de origen del Haber** (para asientos futuros): sueldos y
   prestaciones (`2106` pasivo vs `4201`/`4202` gasto), cargas
   patronales (`2105` vs `4202`), depreciación (`1203` acumulada vs
   `4207` gasto), intangible en desarrollo (`1106`?) e intangible en
   uso (`1107` "Videojuegos terminados" ya mapeado para el traslado).

5. **Alcance de 4102**: qué servicios/licencias directos se capitalizan
   como "servicio_directo". Semilla mapeada; la política de qué cargos
   usan ese concepto sigue por definir.

6. **Tasa de cargas real al cierre**: "saldo de la cuenta de
   prestaciones y cargas patronales / salarios brutos del período" —
   depende del punto 4 (qué cuenta es cada cosa) y de cómo se registren
   los salarios brutos en el mayor.

7. **Base del prorrateo de fondos**: se usaron las horas de desarrollo
   registradas en órdenes abiertas (`RegistroHora`). Confirmar que es
   la base correcta (¿incluir horas de órdenes cerradas? ¿hasta la
   fecha del fondo? hoy se usa `hasta=fondo.fecha`).

8. **Costo de proceso en el período**: hoy se captura manual
   (`CostoProceso` por período). ¿Debe calcularse desde cuentas de
   gasto del mayor en el futuro?

9. **Horas máquina de equipos compartidos**: el uso se captura en
   `UsoEquipo` por fecha; la tasa es cuota_mensual/horas_mes. Confirmar
   que `horas_mes` del equipo es la capacidad correcta y no una jornada
   distinta a la de `ParametroVigente`.

10. **Cierre provisional de costos vs cierre de estados financieros**:
    son independientes (el nuestro no cierra el período). Confirmar que
    el "cierre provisional" del encargo es el de costos y no el CU-07
    existente.
