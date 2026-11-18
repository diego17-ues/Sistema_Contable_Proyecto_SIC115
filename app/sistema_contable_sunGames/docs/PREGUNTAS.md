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
