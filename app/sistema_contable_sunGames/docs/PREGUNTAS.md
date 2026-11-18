# Preguntas pendientes — Subsistema de Costos

## Reestructura R0 (vigente)

Resueltas por el nuevo encargo o por el código:

- **Cuentas destino**: confirmadas en el catálogo — 4101 mano de obra,
  4102 costos directos, 4103 indirectos, 4104 costo de ventas,
  1106 Videojuegos en desarrollo, 1107 Videojuegos terminados y
  1108 Amortización acumulada de videojuegos (Haber del asiento 6).
- **Mecanismo de asientos**: `TransaccionRepository` (patrón
  `ventas.services.contabilizar`); el módulo valida el cuadre antes de
  enviar. No se modifica la contabilidad general.
- **Servicios profesionales**: fuera de la orden (gasto del período);
  se elimina `afecta_mayor` y el "costo de gestión".
- **Fondos, equipos, cortes y ajustes de tasa**: eliminados del módulo.
- **Rol**: `CONTADOR_COSTOS` ya existe en `Rol.choices`.

Abiertas:

1. **Cuenta origen del Haber de mano de obra por proceso** (asiento 1):
   candidatas en catálogo: `2106` Sueldos y prestaciones por pagar
   (pasivo) o las de gasto `4201`/`4202`. ¿Cuál corresponde al pago que
   alimenta la tarifa de cada proceso? `MapeoCuenta` lo permite por
   proceso; falta el mapeo inicial.

2. **Cuentas origen de costos indirectos** (asiento 3): candidatas
   `4203`–`4208` (honorarios no; depreciación 4207, amortización de
   licencias 4208, alquileres 4204, servicios básicos 4205, papelería
   4206) y las no circulantes si procede. ¿Cuáles alimentan el pool y a
   qué proceso se asigna cada una (o reparto por horas totales)?

3. **Anti doble conteo**: la regla compara lo aplicado contra "el saldo
   de la cuenta origen en el período". ¿Saldo = suma neta de
   movimientos del mayor en el período (debe − haber) o solo el debe?
   Asumo **neto del período**; confirmar. ¿El `porcentaje` del mapeo
   reduce la base comparada o solo lo aplicado?

4. **Reapertura del período**: el mayor permite reabrir (Admin +
   contraseña) pero no revierte movimientos. ¿El módulo genera los
   contra-asientos (traslado inverso 1106→41x, amortización inversa)
   con una acción propia en la pantalla de costos, o se añade un punto
   de llamada en `estados_financieros` (eso modifica la contabilidad
   general y requiere tu aprobación)?

5. **Tarifa por hora**: no hay planilla ni costo por hora real por
   empleado/departamento en la contabilidad general, así que se
   conserva `TarifaProceso` propia con vigencia (editable solo por
   Contador de Costos). Si más adelante existe fuente real, se migra.

6. **Procesos iniciales**: semilla Diseño, Programación, Arte, Audio y
   QA (el encargo los marca "a confirmar").

7. **Parámetros de amortización**: `vida_util_anios`=4 (25 % anual) y
   `base_dias_anio`=365, `valor_residual`=0 — **VERIFICAR** la vida
   útil y la política de amortización de videojuegos.

8. **Auxiliar por orden**: `Movimiento` no tiene auxiliar; la orden va
   en `referencia`/`concepto` + `AsientoCosto`. ¿Suficiente o se
   modifica el mayor (requiere aprobación)?

9. **Períodos**: `periodo_de` exige un `PeriodoContable` que cubra la
   fecha del cargo; el módulo no crea períodos. Si falta, el cargo se
   rechaza con aviso de crear el período en Estados financieros.

10. **`estimacion_ref`**: se implementará como FK opcional de solo
    lectura a la versión de presupuesto aprobada de `estimacion`
    (muestra el total estimado, sin variaciones). Es la única lectura
    cruzada permitida entre módulos.

# Preguntas abiertas — Subsistema de Costos / Estimación

Puntos no resueltos en el encargo; se continuó solo con lo definido y se
documenta la decisión tomada para poder revertirla.

1. **Coeficiente de variación**: no se definió sobre qué valores se calcula
   ni con qué desviación estándar. Se usó la desviación estándar
   **poblacional** sobre las horas esperadas PERT de cada experto
   (`cv = pstdev(E_i) / media(E_i)`). ¿Debe ser muestral (n−1) o calcularse
   sobre O/M/P en lugar de E?

2. **Consolidación para presupuesto**: la especificación no dice cómo se
   pasa de N estimaciones por fase/rol a una línea. Se aplicó PERT sobre
   las **medias** de O, M y P de los expertos (`horas_E`, `sigma` de la
   línea). La alternativa es usar la media de las E individuales.
   `desviación del juego = √Σσ²` queda calculable pero aún no se muestra
   en pantalla; falta definir dónde presentarla.

3. **Eficiencia por departamento**: el encargo dice «editable por
   departamento», pero el modelo no tiene departamento en roles ni en
   líneas de mano de obra. Se implementó el parámetro global
   `eficiencia` (0.85). ¿Los roles se agrupan por departamento o la
   eficiencia es por rol/fase?

4. **Alerta por salario faltante**: se registró en bitácora con
   `Resultado.RECHAZADO`. ¿Se requiere una vista/tabla de alertas
   visible para el usuario, o basta la bitácora?

5. **Administración de parámetros y salarios**: el encargo no asigna quién
   los carga. Se dejó disponible para Administrador y Contador de Costos
   dentro del módulo. ¿Debe ser exclusivo del Administrador?

6. **Rondas**: la ronda se crea implícitamente al registrar la primera
   estimación con ese número. ¿Debe existir una acción explícita «iniciar
   ronda» o validación de que los expertos/opiniones de la ronda
   anterior se compartan antes de estimar la siguiente?

7. **Experto vs. Usuario**: `Experto` es un catálogo independiente del
   módulo de usuarios. ¿Debe vincularse a una cuenta de usuario para
   auditoría de quién estimó?

8. **Estados de versión**: se implementaron `BORRADOR → APROBADO →
   VIGENTE` y `VIGENTE → APROBADO` al desplazar la vigente anterior.
   ¿El estado `APROBADO` debe implicar algo más (p. ej. emisión de un
   documento o notificación)?

9. **Costos directos/indirectos estimados**: se capturan por pantalla como
   conceptos libres. ¿Se requiere catálogo de conceptos o importación?

10. **Fecha de vigencia de parámetros en consolidación**: la consolidación
    usa `date.today()` como fecha de vigencia del umbral. Si la ronda se
    cerró en otra fecha, ¿el umbral debe ser el vigente al cierre o al
    día de la consulta?

11. **Fases del juego**: resuelto — fases fijas de SunGames definidas en
    `estimacion/fases.py` según la matriz de funciones entregada; cada
    una con clasificación contable CAPEX/OPEX/MIXTO.

12. **Reglas de corte CAPEX/OPEX**: la matriz define cortes temporales
    (prototipo jugable, Gold Master, timesheet para Dirección de
    producto). La estimación registra la clasificación por fase, pero
    el costeo real (fase posterior) necesitará la fecha de corte por
    juego/título. ¿Dónde se registrará esa fecha (¿catálogo del juego,
    hito del proyecto)?
