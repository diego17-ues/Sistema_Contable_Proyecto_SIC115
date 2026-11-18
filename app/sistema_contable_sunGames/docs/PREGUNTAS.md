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
