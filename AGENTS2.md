Contexto

Estamos construyendo el subsistema de costos de SunGames, empresa de desarrollo de videojuegos. Ya existe una contabilidad general. Este prompt REEMPLAZA los anteriores del módulo de órdenes de trabajo y es la ETAPA 1. Si algo del código existente contradice este prompt, manda este prompt.

Trabajas en local, en la rama costos/ordenes-trabajo. No crees pull requests ni hagas push. Reutiliza docs/DIAGNOSTICO_OT.md y lo que ya averiguaste de la contabilidad general; solo actualízalo si falta algo.

Qué construir (solo esto)

1. Orden de trabajo, una por juego.
2. Registro de los tres elementos del costo: mano de obra directa, costos directos y costos indirectos de desarrollo. Cada registro genera su asiento en la contabilidad general.
3. Vinculación opcional de la orden con una estimación, de solo lectura.
4. Licencias estimadas a vender y costo unitario.
5. Hoja de costos por orden, que es la pantalla principal de la orden.

Elimina del módulo (migraciones reversibles, pruebas actualizadas): cortes de costos, costo de gestión, indicador afecta_mayor, servicios profesionales como cargo, fondos compartidos, registro de equipos, salarios de referencia, ajustes de sobre y subaplicación, cuentas origen y mapeos de reclasificación, y el control de doble conteo.

Fuera de alcance en esta etapa (no los implementes): traslado a Videojuegos en desarrollo, cierre de orden, traslado a Videojuegos terminados, amortización, aplicación automática de indirectos y el módulo de evaluación de rendimiento.

Registro de costos y asientos

Los registros se crean en el módulo de costos y generan su asiento por el mecanismo de la contabilidad general. Nunca escribas directo en las tablas del mayor. La contrapartida se elige en el modal entre las cuentas permitidas del catálogo, con una por defecto para cada elemento.

- Mano de obra directa: fecha, proceso, horas, costo por hora (se propone según el proceso y se puede ajustar). Importe = horas × costo por hora. Asiento: debe 4101, haber la contrapartida (por defecto, sueldos por pagar).
- Costo directo: fecha, proceso opcional, descripción, monto. Asiento: debe 4102, haber la contrapartida (bancos, proveedores o cuentas por pagar).
- Costo indirecto: fecha, proceso opcional, descripción, monto. Asiento: debe 4103, haber la contrapartida (por ejemplo depreciación acumulada, cuentas por pagar o bancos). La depreciación de equipos la calcula la contabilidad general; documenta en docs/PREGUNTAS.md cómo la registra hoy, para no duplicarla.

Cada asiento lleva la orden como auxiliar, guarda su origen (tipo, orden, registro) y una clave de idempotencia por envío de formulario. Todo asiento cuadra. Un registro no se edita ni se borra: se anula, y la anulación genera el contra-asiento. Período cerrado rechaza registros nuevos.

Los códigos de cuenta salen del catálogo mediante una tabla de configuración (elemento, cuenta de costo, contrapartidas permitidas, contrapartida por defecto). No los escribas en el código ni inventes ninguno. Si falta una cuenta, bloquea ese elemento y regístralo en docs/PREGUNTAS.md.

Procesos: catálogo configurable con 5 valores iniciales a confirmar (Diseño, Programación, Arte, Audio y QA). Cada registro lleva un proceso (obligatorio en mano de obra) para poder ver el costo por proceso en la hoja.

Orden de trabajo

Campos: juego, estado, fecha de inicio, licencias_estimadas (entero positivo, editable) y estimacion_ref (referencia opcional de solo lectura a la versión aprobada del módulo de estimación; muestra el total estimado si está disponible). No se calcula ninguna variación: esa comparación la hará otro módulo. Expón una función de lectura resumen_orden(orden_id) que devuelva costo por elemento, costo por proceso, horas por proceso, costo total, licencias estimadas y estimacion_ref, para que ese módulo la use.

Costo unitario = costo total de la orden (sin anulados) / licencias_estimadas. Se calcula con 4 decimales y se muestra con 2. Si no hay licencias estimadas, muestra "—" e indica que se ingresen.

Hoja de costos por orden (pantalla principal de la orden)

- Encabezado: juego, estado, fecha de inicio, estimación vinculada (con su total estimado, si existe), licencias estimadas con botón para editarlas, y costo unitario por licencia.
- Tres secciones, siempre visibles aunque estén vacías: Mano de obra directa, Costos directos y Costos indirectos. Cada línea muestra fecha, proceso, descripción, horas y costo por hora cuando aplica, importe, número de asiento y estado (vigente o anulado). Subtotal por sección.
- Costo total de la orden, en negrita, suma de los tres subtotales.
- Resumen por proceso: tabla con una fila por proceso y una columna por elemento, con totales.
- Botones: Registrar mano de obra, Registrar costo directo, Registrar costo indirecto, y Imprimir (vista de impresión de la hoja).
- Sin pestaña Cortes, sin costo contable ni costo de gestión.

Interfaz

- Reutiliza los componentes, layout y tokens de diseño de la contabilidad general. No introduzcas otra librería de UI.
- Responsive a 360, 768 y 1280 px. En móvil, las tablas pasan a tarjetas y no hay scroll horizontal de página. Botones de al menos 44 px de alto.
- Modales para nueva orden, cada tipo de registro, editar licencias y anular registro. Cierran con Escape, atrapan el foco, validan en línea y deshabilitan guardar mientras se envía. Anular pide confirmación con vista previa del contra-asiento.
- Estados de carga, vacío y error en todas las vistas. Montos con formato de moneda consistente.

Fases

Al terminar cada fase: ejecuta todas las pruebas, haz commit "Etapa 1 · Fase N: <objetivo>", actualiza docs/AVANCE.md y detente.

Fase 1. Limpieza y registro de los tres elementos con sus asientos (modelo, configuración de cuentas, modales, anulación y pruebas).
Fase 2. Hoja de costos, licencias estimadas, costo unitario y vinculación con la estimación. Guarda capturas en docs/capturas/ a 360, 768 y 1280 px. Reinicia el servidor de desarrollo, confirma por escrito que el navegador muestra la hoja nueva y detente para mi revisión.

Pruebas obligatorias (valores exactos)

1. Mano de obra: 40 h × 20.00 = 800.00; asiento debe 4101, haber contrapartida, por 800.00.
2. Costo directo de 1,200.00: debe 4102, haber contrapartida.
3. Costo indirecto de 83.33: debe 4103, haber contrapartida.
4. Costo total de la orden con los tres registros anteriores: 2,083.33.
5. Resumen por proceso: dos registros de programación (800.00 y 500.00) y uno de arte (300.00) dan programación 1,300.00 y arte 300.00.
6. Costo unitario: 120,000.00 / 60,000 = 2.00; sin licencias estimadas muestra "—".
7. Anular un registro genera su contra-asiento y baja el costo total; el registro anulado sigue visible y marcado.
8. Enviar dos veces el mismo formulario no duplica registro ni asiento.
9. Todo asiento cuadra y guarda origen y clave de idempotencia.
10. Período cerrado rechaza registros.
11. La orden con estimacion_ref muestra el total estimado sin calcular variaciones; sin estimación funciona igual.
12. resumen_orden devuelve costo por elemento y por proceso, horas por proceso, total, licencias estimadas y la referencia.
13. No existen en el módulo cortes, costo de gestión, afecta_mayor, fondos, equipos ni salarios de referencia.

Prohibido

- Hardcodear códigos de cuenta, tarifas o porcentajes. Usar float.
- Escribir directo en las tablas del mayor.
- Modificar la contabilidad general o el módulo de estimación sin aprobación escrita en docs/PREGUNTAS.md.
- Decidir por tu cuenta algo no resuelto aquí: regístralo en docs/PREGUNTAS.md.
