# **Especificación de Casos de Uso del Sistema Contable SunGames** 

_Diagrama de Casos de Uso Extendido y pantallas de prototipo_ 

Propósito. Este documento describe los casos del DCU Extendido actualizado y las pantallas de referencia que servirán para elaborar posteriormente los prototipos visuales y el modelo del sistema. 

Alcance. La instrucción vigente del usuario de negocios establece que la información contable se registra directamente en el Libro Mayor y que, después, se genera el Estado de Resultados. Las especificaciones siguen ese flujo. Las pantallas finales no se elaboran en esta etapa. 

Trazabilidad. El DCU actualizado determina los casos y sus relaciones. La Especificación de Requerimientos de Software aporta campos, validaciones y salidas que siguen vigentes; el Modelo de Negocio y el Manual de aplicación del catálogo aportan el contexto de ventas, costos y cuentas. G06_Informe_Etapa2 se usa como referencia de estructura narrativa. 

Criterio de consistencia. La SRS disponible conserva definiciones del esquema contable previo que no coinciden con la instrucción vigente. Este documento aplica el registro directo al Libro Mayor. Cuando las fuentes no definen campos, controles, reglas de corrección o efectos de cierre compatibles con ese flujo, se dejan señalados como pendientes en vez de completar con supuestos. 

## **Interfaz común del prototipo** 

Las pantallas autenticadas comparten encabezado con el nombre del usuario y su rol, menú con opciones autorizadas y área principal. El idioma es español; las fechas usan formato día/mes/año y los importes se expresan en USD con dos decimales. Los campos obligatorios se identifican; los errores se muestran junto al dato y se conservan los demás valores válidos. Los listados se paginan cuando el volumen lo requiere. Las acciones de impacto solicitan confirmación explícita. Estas convenciones proceden de los requisitos comunes de interfaz de la SRS. 

## **Actores del sistema** 

- Administrador: gestiona usuarios y consulta la bitácora; accede a las funciones administrativas del DCU. 

- Contador General: registra y consulta movimientos del Libro Mayor, consulta el catálogo, revisa ventas y genera informes y cierres. 

- Contador de Costos: realiza estimaciones asociadas a videojuegos u órdenes de trabajo. 

- Servicio Steam: actor externo simulado que entrega eventos de venta; las fuentes no describen una conexión real. 

## **Especificación de casos de uso** 

Se documentan 32 casos, con los nombres y relaciones del diagrama actualizado. 

### **CU-01 - Iniciar sesión** 

**Actores:** Administrador, Contador General y Contador de Costos **Prioridad / Fuente:** No indicada en el DCU | SRS RF-003 

#### **Descripción** 

Permite a un usuario registrado y activo acceder a las opciones autorizadas para su rol. 

#### **Pantallas del caso** 

#### **Acceso al sistema** 

- Campos obligatorios Usuario y Contraseña; la contraseña se muestra oculta. 

- Botón Iniciar sesión. Antes de autenticar no se presenta el menú de módulos. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

- Los errores se muestran sin revelar cuál credencial falló. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario abre la dirección web. 

2. El sistema presenta Usuario, Contraseña e Iniciar sesión. 

3. El usuario ingresa sus credenciales y envía el formulario. 

4. El sistema valida los campos, las credenciales y el estado de la cuenta. 

5. Si la cuenta está activa, se crea la sesión, se registra el acceso y se abre el área inicial del rol con su menú autorizado. 

#### **Flujos Alternativos** 

- Campo vacío: se señala el campo y se conservan los otros datos. 

- Credenciales incorrectas: se deniega el acceso con el mensaje general definido en RF-003. 

- Cuenta inactiva o bloqueada: se informa que no está habilitada. 

- Falla del servicio de autenticación: no se crea sesión y se informa el error. 

#### **Precondiciones** 

- El usuario está registrado y tiene un rol válido. 

- El servicio de autenticación está disponible. 

#### **Poscondiciones** 

- La sesión queda activa si las credenciales son válidas. 

- El intento queda registrado en la bitácora. 

#### **Relaciones** 

Precondición de los casos autenticados. 

### **CU-02 - Administrar Usuarios del Sistema** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-001 y RF-002 

#### **Descripción** 

Reúne las funciones para consultar usuarios, agregar cuentas y desactivar usuarios. 

#### **Pantallas del caso** 

#### **Usuarios del sistema** 

- Tabla con nombre de usuario, nombre completo, rol y estado. 

- Acciones: Agregar usuario, Consultar Usuarios y Desactivar Usuario. 

- El listado se pagina cuando el volumen lo requiere. La SRS no define filtros de búsqueda para usuarios. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador abre Usuarios del Sistema. 

2. El sistema muestra el listado y las acciones del DCU. 

3. El Administrador selecciona una acción. 

4. El sistema abre el caso de extensión y, al concluir, actualiza el listado. 

#### **Flujos Alternativos** 

- Usuario sin rol autorizado: se bloquea el acceso. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

- Sin usuarios registrados: se muestra el resultado vacío. 

#### **Precondiciones** 

- El Administrador inició sesión. 

- El rol permite administrar usuarios. 

#### **Poscondiciones** 

- Los cambios confirmados se reflejan en el listado y en la bitácora. 

#### **Relaciones** 

Caso base; Agregar, Desactivar y Consultar Usuarios lo extienden. 

### **CU-02.1 - Agregar Usuario** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-001 y RF-002 

#### **Descripción** 

Registra un usuario nuevo y le asigna uno de los roles definidos. 

#### **Pantallas del caso** 

#### **Formulario de alta** 

- Campos: nombre de usuario, nombre completo y rol (Administrador, Contador General o Contador de Costos). 

- Nombre de usuario y nombre completo son obligatorios; el nombre de usuario admite hasta ocho caracteres y debe ser único. 

- La cuenta se registra activa. La SRS no define aquí una pantalla para establecer la contraseña. 

- Acciones: Guardar y volver al listado. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador selecciona Agregar usuario. 

2. El sistema muestra el formulario. 

3. El Administrador completa usuario, nombre y rol y solicita guardar. 

4. El sistema valida obligatoriedad, longitud, unicidad y rol. 

5. El sistema registra la cuenta activa y el evento en la bitácora. 

6. El sistema confirma el alta y actualiza el listado. 

#### **Flujos Alternativos** 

- Faltan datos: se señalan los campos. 

- El nombre ya existe o supera la longitud permitida: se rechaza el alta. 

- Rol no válido: se solicita una opción permitida. 

- Falla el guardado: no se crea la cuenta. 

#### **Precondiciones** 

- El Administrador tiene una sesión activa. 

#### **Poscondiciones** 

- El usuario queda activo con un rol asignado y el alta se registra en bitácora. 

#### **Relaciones** 

Extiende Administrar Usuarios del Sistema. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

### **CU-02.2 - Desactivar Usuario** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-001 

#### **Descripción** 

Desactiva una cuenta para impedir nuevos inicios de sesión, conservando su registro. 

#### **Pantallas del caso** 

#### **Confirmación de desactivación** 

- Resumen: usuario, nombre completo, rol y estado actual. 

- Acciones Confirmar desactivación y Cancelar. 

- El cambio de estado se registra en bitácora; no se ofrece edición de otros datos en esta pantalla. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador elige Desactivar en una fila. 

2. El sistema presenta el resumen y solicita confirmación. 

3. El Administrador confirma. 

4. El sistema valida el estado, cambia la cuenta a inactiva y registra la acción. 

5. El sistema informa el resultado y actualiza la fila. 

#### **Flujos Alternativos** 

- El Administrador cancela: no hay cambios. 

- El usuario ya está inactivo o la acción no aplica a su estado: se informa la causa. 

- Falla el guardado: se conserva el estado anterior. 

#### **Precondiciones** 

- El Administrador está autenticado. 

- El usuario seleccionado existe. 

#### **Poscondiciones** 

- La cuenta queda inactiva y su historial se conserva. 

#### **Relaciones** 

Extiende Administrar Usuarios del Sistema. 

### **CU-02.3 - Consultar Usuarios** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-001 y RF-002 

#### **Descripción** 

Presenta las cuentas registradas, sus roles y su estado. 

#### **Pantallas del caso** 

#### **Consulta de usuarios** 

- Tabla con nombre de usuario, nombre completo, rol y estado. 

- La ficha de un registro presenta esos mismos datos. 

- Los criterios de filtro no están definidos en la SRS y no se fijan aquí. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador selecciona Consultar Usuarios. 

2. El sistema presenta las cuentas disponibles. 

3. El Administrador abre una fila. 

4. El sistema muestra la ficha sin modificarla. 

#### **Flujos Alternativos** 

- No hay cuentas: se muestra un listado vacío. 

- Falla la consulta: se informa el error. 

#### **Precondiciones** 

- El Administrador tiene sesión activa. 

#### **Poscondiciones** 

- Los datos quedan visibles y no cambian. 

#### **Relaciones** 

Extiende Administrar Usuarios del Sistema. 

### **CU-03 - Control de Auditoría** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; bitácora de operaciones descrita en la SRS 

#### **Descripción** 

Permite revisar la actividad registrada y abrir las opciones de consulta y descarga de la bitácora. 

#### **Pantallas del caso** 

#### **Panel de auditoría** 

- Listado con fecha y hora, usuario actor, usuario afectado cuando corresponda, acción y resultado, según los datos de bitácora disponibles. 

- Acciones: Consultar Logs de Auditoría y Descargar Logs. 

- Los filtros no están detallados en las fuentes y no se inventan aquí. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador abre Control de Auditoría. 

2. El sistema presenta los eventos disponibles. 

3. El Administrador selecciona consultar o descargar. 

4. El sistema abre el caso correspondiente. 

#### **Flujos Alternativos** 

- No hay eventos: se informa que el listado está vacío. 

- La bitácora no está disponible: se informa el error sin alterar registros. 

#### **Precondiciones** 

- El Administrador inició sesión y tiene permiso de auditoría. 

#### **Poscondiciones** 

- La bitácora queda disponible para lectura; sus eventos no cambian. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Relaciones** 

Caso base; Consultar Logs y Descargar Logs lo extienden. 

### **CU-03.1 - Consultar Logs de Auditoría** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; bitácora descrita en la SRS 

#### **Descripción** 

Muestra los eventos conservados en la bitácora para su revisión. 

#### **Pantallas del caso** 

#### **Listado de logs** 

- Columnas disponibles: fecha y hora, usuario actor, usuario afectado si aplica, acción y resultado. 

- El detalle muestra la información almacenada para el evento. 

- No se definen filtros ni un orden específico en las fuentes. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador selecciona Consultar Logs. 

2. El sistema presenta los eventos de auditoría. 

3. El Administrador abre un evento y revisa sus datos. 

4. El Administrador vuelve al listado. 

#### **Flujos Alternativos** 

- No hay eventos: se presenta el resultado vacío. 

- Falla la recuperación: se informa el error y los datos permanecen intactos. 

#### **Precondiciones** 

- El Administrador tiene sesión activa. 

#### **Poscondiciones** 

- Los eventos consultados no se modifican. 

#### **Relaciones** 

Extiende Control de Auditoría. 

### **CU-03.2 - Descargar Logs** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU Extendido 

#### **Descripción** 

Prepara la descarga de los eventos de auditoría en los formatos que muestra el diagrama. 

#### **Pantallas del caso** 

#### **Selección de formato** 

- Opciones: Descargar PDF y Descargar Excel. 

- El contenido corresponde a los eventos disponibles y sus campos de bitácora. 

- Nombre de archivo, plantilla e intervalo predeterminado no están definidos en las fuentes. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador selecciona Descargar Logs. 

2. El sistema presenta las opciones PDF y Excel. 

3. El Administrador elige un formato. 

4. El sistema genera el archivo y lo ofrece al navegador. 

#### **Flujos Alternativos** 

- No hay eventos: se informa que el resultado no contiene registros. 

- Falla la generación: se muestra el error y se conserva la selección. 

#### **Precondiciones** 

- El Administrador tiene sesión activa. 

- La bitácora está disponible. 

#### **Poscondiciones** 

- El archivo queda disponible; la bitácora original no cambia. 

#### **Relaciones** 

Extiende Control de Auditoría; PDF y Excel extienden este caso. 

### **CU-03.2.1 - Descargar PDF** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU Extendido 

#### **Descripción** 

Genera en PDF los eventos de auditoría seleccionados. 

#### **Pantallas del caso** 

#### **Preparación de PDF** 

- Acción disponible desde Descargar Logs. 

- El archivo contiene los campos existentes para cada evento. 

- La plantilla y el nombre del archivo no se especifican en las fuentes. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador elige PDF. 

2. El sistema prepara los eventos disponibles. 

3. El sistema ofrece el archivo y comunica el resultado. 

#### **Flujos Alternativos** 

- Sin eventos: no se genera un archivo vacío sin informar al usuario. 

- Falla la generación: se muestra el error y se conserva la consulta. 

#### **Precondiciones** 

- Existe una consulta de auditoría disponible. 

#### **Poscondiciones** 

- El PDF puede descargarse y no altera la bitácora. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Relaciones** 

Extiende Descargar Logs. 

### **CU-03.2.2 - Descargar Excel** 

**Actores:** Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU Extendido 

#### **Descripción** 

Genera en Excel los eventos de auditoría seleccionados. 

#### **Pantallas del caso** 

#### **Preparación de Excel** 

- Acción disponible desde Descargar Logs. 

- La hoja presenta una fila por evento y los campos existentes en bitácora. 

- No se fijan plantilla ni nombre de archivo en las fuentes. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Administrador elige Excel. 

2. El sistema prepara el archivo con los eventos disponibles. 

3. El sistema ofrece el archivo y comunica el resultado. 

#### **Flujos Alternativos** 

- Sin eventos: se informa que no hay contenido. 

- Falla la generación: se muestra el error y se conserva la consulta. 

#### **Precondiciones** 

- Existe una consulta de auditoría disponible. 

#### **Poscondiciones** 

- El archivo puede descargarse y no altera la bitácora. 

#### **Relaciones** 

Extiende Descargar Logs. 

### **CU-04 - Generar Libro** 

**Actores:** Administrador y Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-018 a RF-020; instrucción vigente de registro directo al Libro Mayor 

#### **Descripción** 

Genera consultas del Libro Mayor o del balance de comprobación para el período solicitado. 

#### **Pantallas del caso** 

#### **Selección de reporte** 

- Opciones: Libro Mayor y Balance de Comprobación, según el DCU. 

- Campos de fecha inicial y final; para consultar el Libro Mayor se indica también la cuenta. 

- Botón Generar y área de resultado. Esta pantalla consulta registros existentes y no registra nuevos movimientos. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario abre Generar Libro. 

2. El sistema presenta los tipos de reporte y criterios aplicables. 

3. El usuario elige el reporte e ingresa fechas y, si aplica, cuenta. 

4. El sistema valida criterios y consulta movimientos del Libro Mayor. 

5. El sistema presenta el resultado; para Balance de Comprobación ejecuta el caso incluido. 

#### **Flujos Alternativos** 

- Fechas inválidas o rango invertido: se señalan los campos. 

- No hay movimientos: se informa que el resultado está vacío. 

- Falla la consulta: se informa el error sin cambiar registros. 

#### **Precondiciones** 

- El usuario está autenticado y autorizado para consulta contable. 

#### **Poscondiciones** 

- El reporte queda visible; la consulta no modifica el Libro Mayor. 

#### **Relaciones** 

Crear Balance de Comprobación se incluye; Generar Libro y Consultar Libro se relacionan con Libro Mayor. 

### **CU-04.1 - Crear Balance de Comprobación** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-019, ajustado a la instrucción vigente 

#### **Descripción** 

Presenta saldos por cuenta para el rango indicado, obtenidos de los movimientos del Libro Mayor. 

#### **Pantallas del caso** 

#### **Balance de comprobación** 

- Criterios: fecha inicial y fecha final válidas. 

- Resultado organizado por código y denominación de cuenta con los saldos disponibles. 

- La SRS anterior especifica columnas deudoras y acreedoras y una prueba de igualdad. La presentación y la regla de revisión compatibles con el registro directo todavía no están definidas; no se usa la igualdad como bloqueo. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador indica el período. 

2. El sistema valida las fechas. 

3. El sistema obtiene las cuentas con movimientos o saldos. 

4. El sistema presenta la vista de saldos por cuenta. 

#### **Flujos Alternativos** 

- Rango invertido: se indica qué corregir. 

- Sin movimientos: se informa el resultado vacío. 

- No se bloquea por una desigualdad entre columnas; ese criterio requiere actualizar la SRS. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Precondiciones** 

- El Contador General tiene sesión activa y permiso de consulta. 

#### **Poscondiciones** 

- El reporte queda visible sin alterar los registros del Libro Mayor. 

#### **Relaciones** 

Incluido por Generar Libro. 

### **CU-04.2 - Consultar Libro** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-018 

#### **Descripción** 

Permite localizar y revisar movimientos registrados directamente en el Libro Mayor. 

#### **Pantallas del caso** 

#### **Consulta del Libro Mayor** 

- Filtros documentados: cuenta, fecha inicial y fecha final. 

- Resultados cronológicos con fecha, cuenta, concepto y valores conservados por el libro. 

- La SRS anterior identifica debe y haber como valores de consulta; no se agregan referencias a registros intermedios. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario selecciona Consultar Libro. 

2. El sistema muestra cuenta y rango de fechas. 

3. El usuario completa los criterios y solicita la consulta. 

4. El sistema valida cuenta y rango, recupera los movimientos y muestra el resultado. 

#### **Flujos Alternativos** 

- Cuenta o fechas no válidas: se señala el criterio. 

- Sin coincidencias: se presenta un resultado vacío. 

- Falla la consulta: se informa el error. 

#### **Precondiciones** 

- El usuario tiene permiso de consulta al Libro Mayor. 

#### **Poscondiciones** 

- La consulta no modifica el libro. 

#### **Relaciones** 

Extiende Libro Mayor y se relaciona con Generar Libro. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

### **CU-05 - Libro Mayor** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; decisión vigente del usuario de negocios; SRS RF-017 y RF-018 para consulta 

#### **Descripción** 

Permite registrar movimientos contables sobre cuentas de detalle. Cada movimiento tiene cuenta, fecha, concepto e importe firmado. Varios movimientos pueden agruparse en una transacción para consulta. El sistema valida cada movimiento, pero no exige que las transacciones cuadren al registrarse: esa verificación corresponde al Balance de comprobación.
#### **Pantallas del caso** 

#### **Registro y consulta del Libro Mayor** 

- Formulario de registro directo: cuenta del catálogo, fecha, concepto y valor del movimiento. 

- La SRS anterior describe debe y haber para consulta, pero no actualiza si el importe nuevo se captura como un valor con sentido o mediante esas columnas; tampoco define correcciones posteriores. 

- Listado por cuenta y rango de fechas con fecha, concepto, valores guardados y saldo disponible. 

- Acciones: Registrar movimiento, Consultar Libro y Consultar Saldo de Cuentas. No se muestran correlativos ni referencias a un registro intermedio. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Contador General abre Libro Mayor. 

2. El sistema presenta el formulario de registro directo y la consulta. 

3. El usuario selecciona una cuenta, indica fecha, concepto y valor según la representación disponible, y solicita guardar. 

4. El sistema valida cuenta, fecha y estado del período. 

5. El sistema guarda el movimiento directamente en el Libro Mayor y confirma el resultado. 

6. El usuario puede consultar el movimiento o el saldo de la cuenta. 

#### **Flujos Alternativos** 

- Cuenta no válida o inactiva: no se guarda y se señala la cuenta. 

- Fecha inválida o período cerrado: se rechaza y se informa la causa. 

- Faltan datos: se señalan los campos y se conservan los datos válidos. 

- Falla el guardado: se informa el error sin confirmar el registro. 

#### **Precondiciones** 

- El Contador General tiene sesión activa. 

- El catálogo de cuentas está disponible. 

#### **Poscondiciones** 

- El movimiento confirmado queda directamente en el Libro Mayor y disponible para reportes. 

#### **Relaciones** 

Consultar Libro, Consultar Saldo de Cuentas y Generar Libro se relacionan con este caso. 

### **CU-05.1 - Consultar Saldo de Cuentas** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-017 

#### **Descripción** 

Muestra el saldo acumulado de una cuenta a la fecha de corte solicitada. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Pantallas del caso** 

#### **Saldo de cuenta** 

- Criterios: cuenta y fecha de corte. 

- Resultado con código, denominación, fecha consultada, componentes disponibles y saldo acumulado. 

- La SRS anterior enumera debe y haber; su presentación queda sujeta a la actualización del formato de registro directo. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario abre Consultar Saldo de Cuentas desde Libro Mayor. 

2. El sistema solicita cuenta y fecha de corte. 

3. El usuario completa los criterios y consulta. 

4. El sistema valida, recupera los movimientos hasta la fecha y muestra el saldo. 

#### **Flujos Alternativos** 

- Cuenta inexistente o fecha inválida: se señala el campo. 

- Sin movimientos: se muestra el saldo disponible, incluido cero cuando corresponda. 

#### **Precondiciones** 

- El usuario tiene acceso autenticado al Libro Mayor. 

#### **Poscondiciones** 

- El saldo queda visible sin alterar movimientos. 

#### **Relaciones** 

Extiende Libro Mayor. 

### **CU-06 - Catálogo de Cuentas** 

**Actores:** Administrador y Contador General autorizado 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-005 y RF-009 a RF-010; Manual del catálogo 

#### **Descripción** 

Presenta el catálogo vigente y permite consultar, registrar, modificar o dar de baja cuentas con autorización. 

#### **Pantallas del caso** 

#### **Catálogo de cuentas** 

- Tabla: código, denominación, elemento o rubro, naturaleza y estado. 

- Filtros definidos: código, denominación, rubro, naturaleza y estado. 

- El detalle muestra descripción y reglas de uso. No se permiten subcuentas. 

- Acciones: Registrar Cuenta, Modificar Cuenta y Eliminar Cuenta; la baja es desactivación lógica según RF-008. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario abre Catálogo de Cuentas. 

2. El sistema muestra las cuentas y criterios. 

3. El usuario consulta una cuenta o selecciona una acción. 

4. El sistema ejecuta el caso de extensión y actualiza la lista cuando termina. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Flujos Alternativos** 

- Sin coincidencias: se informa que no hay cuentas para los criterios. 

- Filtro inválido: se señala el campo. 

- Usuario sin permiso: se bloquea la modificación. 

#### **Precondiciones** 

- El usuario inició sesión; para cambios, tiene autorización. 

#### **Poscondiciones** 

- El catálogo queda disponible para consulta y conserva el historial de cambios. 

#### **Relaciones** 

Registrar, Eliminar y Modificar Cuenta extienden este caso. 

### **CU-06.1 - Registrar Cuenta** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-006 y RF-010; Manual del catálogo 

#### **Descripción** 

Registra una cuenta nueva con solicitud justificada y aprobación de Junta Directiva. 

#### **Pantallas del caso** 

#### **Solicitud y alta** 

- Datos: denominación propuesta, rubro y grupo, naturaleza, descripción y reglas de uso. 

- Documentación: justificación, referencia de respaldo y acuerdo de Junta Directiva con número y fecha. 

- El sistema asigna el siguiente código disponible del grupo; no se captura ni reutiliza manualmente. 

- El formulario no admite subcuentas y valida duplicidad y correspondencia con el catálogo. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador selecciona Registrar Cuenta. 

2. El sistema muestra el formulario y los datos de respaldo. 

3. El contador completa la solicitud. 

4. El sistema valida catálogo, naturaleza, duplicidad, justificación y aprobación. 

5. El sistema asigna el código, registra la cuenta activa y anota el alta en bitácora. 

6. El sistema confirma y vuelve al catálogo. 

#### **Flujos Alternativos** 

- Falta justificación, respaldo o aprobación: se señala el dato pendiente. 

- Cuenta duplicada o equivalente: se bloquea el alta. 

- Rubro o naturaleza inválidos: se informa la regla. 

- No puede asignarse código: no se registra la cuenta. 

#### **Precondiciones** 

- El usuario está autorizado y existe una solicitud y aprobación de Junta Directiva. 

#### **Poscondiciones** 

- La cuenta activa queda asociada al código, rubro y grupo aprobados. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Relaciones** 

Extiende Catálogo de Cuentas. 

### **CU-06.2 - Eliminar Cuenta** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-008; Manual del catálogo 

#### **Descripción** 

Da de baja lógicamente una cuenta que cumple las condiciones establecidas. El nombre del caso en el DCU no implica eliminación física. 

#### **Pantallas del caso** 

#### **Solicitud de baja** 

- Resumen: código, denominación, rubro, naturaleza y estado. 

- El sistema muestra saldo y existencia de movimientos del ejercicio, requeridos por RF-008. 

- Campos: justificación, documento de respaldo y acuerdo de Junta Directiva (número y fecha). 

- Confirmar cambia el estado a inactiva y conserva movimientos e historial. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador selecciona una cuenta y solicita Eliminar Cuenta. 

2. El sistema consulta estado, saldo y movimientos del ejercicio. 

3. El sistema presenta los resultados y pide justificación y referencias de aprobación. 

4. El contador confirma. 

5. Si se cumplen las condiciones, el sistema desactiva la cuenta y registra la acción. 

#### **Flujos Alternativos** 

- Cuenta inexistente o inactiva: no continúa. 

- Saldo distinto de cero o movimientos en el ejercicio: no permite la baja. 

- Falta documentación o aprobación: señala el dato pendiente. 

- El usuario cancela: no hay cambios. 

#### **Precondiciones** 

- El contador está autenticado y autorizado; la cuenta existe y está activa. 

#### **Poscondiciones** 

- La cuenta queda inactiva si cumple las reglas; su historial permanece. 

#### **Relaciones** 

Extiende Catálogo de Cuentas. 

### **CU-06.3 - Modificar Cuenta** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-007 y RF-010; Manual del catálogo 

#### **Descripción** 

Actualiza los datos permitidos de una cuenta conservando su código. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Pantallas del caso** 

#### **Edición de cuenta** 

- La ficha presenta código, denominación, rubro, naturaleza, descripción y reglas de uso. 

- Se pueden proponer cambios en denominación, rubro, naturaleza, descripción y reglas; el código es de solo lectura. 

- Se requieren justificación, respaldo y acuerdo de Junta Directiva con número y fecha. 

- La pantalla permite revisar los datos propuestos antes de guardar. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador selecciona una cuenta y solicita modificarla. 

2. El sistema presenta los valores actuales y campos editables. 

3. El contador ingresa cambios y respaldo de aprobación. 

4. El sistema valida existencia, unicidad, rubro, naturaleza y documentación. 

5. El sistema guarda conservando el código y registra el cambio en bitácora. 

#### **Flujos Alternativos** 

- Código bloqueado: no puede modificarse. 

- Denominación duplicada o rubro/naturaleza inválidos: no se guardan cambios. 

- Falta documentación: se señala el dato pendiente. 

- Falla el guardado: se conservan los valores anteriores. 

#### **Precondiciones** 

- El usuario está autenticado y autorizado; la cuenta existe. 

#### **Poscondiciones** 

- La cuenta queda modificada con su código original y cambio auditado. 

#### **Relaciones** 

Extiende Catálogo de Cuentas. 

### **CU-07 - Estados Financieros** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-038, RF-039, RF-040, RF-043 y RF-044; información consultada del Libro Mayor 

#### **Descripción** 

Agrupa las opciones de estados financieros y cierres que aparecen en el diagrama. 

#### **Pantallas del caso** 

#### **Menú de estados y cierres** 

- Opciones: Cierre Contable, Cierre Provisional, Hoja de Trabajo, Cierre Anual, Estado de Resultados, Estado de Cambios en el Patrimonio y Balance General. 

- Cada opción abre su propio caso y solicita el período o fecha correspondiente. 

- Los informes consultan el Libro Mayor y este menú no registra movimientos por sí solo. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Contador General abre Estados Financieros. 

2. El sistema presenta las opciones del DCU. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

3. El usuario elige una opción. 

4. El sistema abre el caso y presenta sus criterios o resultado. 

#### **Flujos Alternativos** 

- Opción no autorizada: se impide el acceso. 

- No hay datos consultables: el caso seleccionado informa que no hay resultados. 

#### **Precondiciones** 

- El Contador General inició sesión. 

- El Libro Mayor está disponible para consulta. 

#### **Poscondiciones** 

- El informe o proceso seleccionado queda presentado; este caso no modifica los registros. 

#### **Relaciones** 

Agrupa los casos de cierre e informes según el DCU. 

### **CU-07.1 - Cierre Contable** 

**Actores:** Contador General y Administrador 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-014 Control de apertura y cierre de períodos; requisito Validación de requisitos previos al cierre mensual (identificador duplicado en la SRS) 

#### **Descripción** 

Valida y cambia el estado de un período contable conforme a los controles de apertura y cierre. 

#### **Pantallas del caso** 

#### **Control de período** 

- Datos: fecha inicial, fecha final, tipo mensual o anual y estado actual. 

- Acciones: Validar período y Solicitar cierre. El sistema presenta condiciones cumplidas y pendientes. 

- La confirmación es explícita. Un período cerrado bloquea registros nuevos para esas fechas, conforme a RF-014. 

- Las fuentes actualizadas no definen movimientos automáticos como efecto del cierre; no se agregan en esta pantalla. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario abre Cierre Contable y selecciona un período. 

2. El sistema muestra rango y estado. 

3. El usuario solicita validar. 

4. El sistema verifica los criterios disponibles y presenta pendientes. 

5. Si procede, el usuario confirma y el sistema actualiza el estado del período. 

#### **Flujos Alternativos** 

- Período inexistente, cerrado o fechas inválidas: se informa y no se repite la acción. 

- Hay condiciones pendientes: se listan y no se cierra el período. 

- Falla la actualización: no se confirma el cambio. 

#### **Precondiciones** 

- El usuario tiene rol autorizado y sesión activa. 

- El período existe y está abierto. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Poscondiciones** 

- El período queda cerrado cuando se cumplen las validaciones y no admite nuevos registros. 

#### **Relaciones** 

Cierre Provisional extiende este caso; relacionado con Estados Financieros. 

### **CU-07.2 - Cierre Provisional** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-014 y RF-044, con los efectos no definidos pendientes 

#### **Descripción** 

Prepara la revisión provisional de un período y permite abrir la Hoja de Trabajo. 

#### **Pantallas del caso** 

#### **Preparación del cierre provisional** 

- Criterios: fecha inicial y final, tipo de período y estado. 

- Panel con resultado de las validaciones disponibles. 

- Acción Generar Hoja de Trabajo. 

- Las fuentes anteriores asocian el cierre a efectos no definidos para el registro directo; esta pantalla no incorpora campos ni movimientos supuestos. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador selecciona Cierre Provisional. 

2. El sistema solicita rango y muestra estado del período. 

3. El contador indica el rango y pide la revisión. 

4. El sistema valida las fechas y consulta el Libro Mayor. 

5. El sistema abre Hoja de Trabajo y presenta el resultado para revisión. 

#### **Flujos Alternativos** 

- Rango inválido o período no consultable: no prepara el reporte. 

- Sin movimientos: se informa que no hay datos para la hoja. 

- Falla la consulta: se informa el error sin modificar el libro. 

#### **Precondiciones** 

- El contador tiene sesión activa; el período existe y se puede consultar. 

#### **Poscondiciones** 

- La revisión provisional queda disponible sin generar movimientos automáticos. 

#### **Relaciones** 

Extiende Cierre Contable e incluye Hoja de Trabajo. 

### **CU-07.2.1 - Hoja de Trabajo** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-044 como antecedente de reporte 

#### **Descripción** 

Presenta para revisión la información contable del período seleccionado. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Pantallas del caso** 

#### **Vista de Hoja de Trabajo** 

- Encabezado con el período solicitado. 

- Área de resultado con datos consultados desde el Libro Mayor. 

- Las fuentes actualizadas no definen las columnas ni cálculos de la hoja bajo el registro directo; no se enumera una estructura supuesta. 

- La SRS menciona exportación, pero no determina formato o diseño del archivo. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El caso recibe un período desde Cierre Provisional o Cierre Anual. 

2. El sistema consulta los registros del Libro Mayor. 

3. El sistema presenta la hoja para revisión. 

4. El contador vuelve al caso de cierre. 

#### **Flujos Alternativos** 

- Período sin movimientos: resultado vacío. 

- Falla la consulta: se informa el error y no cambia el Libro Mayor. 

#### **Precondiciones** 

- Se recibió un período válido desde un caso de cierre. 

#### **Poscondiciones** 

- La hoja queda disponible para consulta. 

#### **Relaciones** 

Incluida por Cierre Provisional y relacionada con Cierre Anual en el DCU. 

### **CU-07.3 - Cierre Anual** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-043 y RF-014, con actualización pendiente 

#### **Descripción** 

Permite revisar el ejercicio anual y los informes financieros relacionados antes de solicitar el cierre. 

#### **Pantallas del caso** 

#### **Revisión del cierre anual** 

- Criterio: ejercicio o rango anual y estado del período. 

- Informes vinculados en el DCU: Estado de Resultados, Estado de Cambios en el Patrimonio, Balance General y Hoja de Trabajo cuando corresponda. 

- El sistema consulta el Libro Mayor y presenta las condiciones disponibles. 

- Las fuentes anteriores definen efectos anuales que no coinciden con la instrucción vigente; su reemplazo no está especificado y no se modela aquí. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador selecciona Cierre Anual e indica el ejercicio. 

2. El sistema verifica el ejercicio y consulta el Libro Mayor. 

3. El sistema presenta los informes relacionados para revisión. 

4. El contador solicita el cierre. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

5. El sistema comunica si el período está listo o qué validación sigue pendiente. 

#### **Flujos Alternativos** 

- Ejercicio inexistente o ya cerrado: se informa su estado. 

- Faltan datos para un informe: se indica cuál no puede generarse. 

- No se generan efectos contables no definidos en las fuentes actualizadas. 

#### **Precondiciones** 

- El Contador General está autenticado y el ejercicio es consultable. 

#### **Poscondiciones** 

- El resultado de revisión queda disponible; el estado del período se gestiona mediante el caso de cierre vigente. 

#### **Relaciones** 

Incluye informes relacionados señalados por el DCU y se relaciona con Hoja de Trabajo. 

### **CU-07.4 - Estado de Cambios en el Patrimonio** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-040 

#### **Descripción** 

Genera el estado del período usando las cuentas patrimoniales y los movimientos del Libro Mayor. 

#### **Pantallas del caso** 

#### **Estado de cambios en el patrimonio** 

- Criterios: fecha inicial y final. 

- Resultado por cuenta patrimonial con saldos iniciales, movimientos del período y saldos finales, conforme a RF-040. 

- El período y los totales disponibles quedan visibles en la pantalla. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El usuario abre Estado de Cambios en el Patrimonio. 

2. El sistema solicita el período. 

3. El contador ingresa las fechas y solicita generar. 

4. El sistema valida el rango y consulta cuentas patrimoniales y el resultado registrado. 

5. El sistema presenta saldos iniciales, movimientos y saldos finales. 

#### **Flujos Alternativos** 

- Fechas faltantes, inválidas o invertidas: se señalan. 

- Período no consultable: se informa la condición. 

- Sin movimientos patrimoniales: se muestran los saldos disponibles sin movimientos. 

#### **Precondiciones** 

- El Contador General tiene sesión activa; el catálogo identifica cuentas patrimoniales. 

#### **Poscondiciones** 

- El estado queda visible sin alterar el Libro Mayor. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Relaciones** 

Relacionado con los cierres que lo incluyen en el DCU. 

### **CU-07.5 - Estado de Resultados** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-039; instrucción vigente del usuario de negocios 

#### **Descripción** 

Genera el resultado del período a partir de los movimientos de ingresos y egresos registrados directamente en el Libro Mayor. 

#### **Pantallas del caso** 

#### **Estado de resultados** 

- Criterios obligatorios: fecha inicial y final; la primera no puede ser posterior a la segunda. 

- Reporte con las cuentas y los importes que componen ventas netas, utilidad bruta, utilidad de operación y resultado final, según RF-039. 

- La pantalla identifica el período y muestra cada subtotal y las cuentas que lo forman. 

- Se genera después del registro directo en el Libro Mayor; esta consulta no modifica los movimientos. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. Después de registrar movimientos, el contador abre Estado de Resultados. 

2. El sistema solicita el período. 

3. El contador ingresa fechas y solicita generar. 

4. El sistema valida el rango y consulta las cuentas de ingresos y egresos. 

5. El sistema calcula y presenta los subtotales, las cuentas componentes y el resultado final. 

#### **Flujos Alternativos** 

- Fechas faltantes, inválidas o invertidas: se señala el criterio. 

- Rango no consultable: se informa la condición. 

- Sin movimientos de resultados: se presenta el resultado vacío o los saldos disponibles, sin crear registros. 

#### **Precondiciones** 

- El usuario tiene rol Contador General y sesión activa. 

- Los movimientos del período, si existen, están consultables en el Libro Mayor. 

#### **Poscondiciones** 

- El Estado de Resultados queda visible y se obtiene de los movimientos existentes. 

#### **Relaciones** 

Relacionado con Estados Financieros y con Cierre Anual según el DCU. 

### **CU-07.6 - Balance General** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-038, con saldos del Libro Mayor 

#### **Descripción** 

Genera una vista de la situación financiera a la fecha de corte indicada, clasificada según el catálogo. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Pantallas del caso** 

#### **Balance general** 

- Campo obligatorio: fecha de corte. 

- Reporte por categorías del catálogo con las cuentas, saldos y totales disponibles. 

- La clasificación procede del catálogo vigente y de las decisiones documentadas para SunGames. 

- La SRS anterior incluía una igualdad global como prueba; no se aplica como bloqueo hasta que el criterio se actualice al registro directo. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador abre Balance General. 

2. El sistema solicita fecha de corte. 

3. El contador indica una fecha válida y solicita generar. 

4. El sistema consulta saldos y clasifica las cuentas por catálogo. 

5. El sistema presenta cuentas, saldos y totales. 

#### **Flujos Alternativos** 

- Fecha faltante o inválida: se señala el campo. 

- Fecha fuera del período consultable: se informa la restricción. 

- Sin saldos: se presenta el resultado disponible sin modificar el libro. 

#### **Precondiciones** 

- El usuario tiene rol Contador General y sesión activa; el catálogo está disponible. 

#### **Poscondiciones** 

- El reporte queda visible sin cambios al Libro Mayor. 

#### **Relaciones** 

Relacionado con los cierres que lo incluyen en el DCU. 

### **CU-08 - Verificar Ventas** 

**Actores:** Contador General y Servicio Steam simulado 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-021 y RF-022; simulación Steam descrita en la SRS 

#### **Descripción** 

Permite revisar las ventas recibidas desde la simulación Steam antes de decidir su registro en el Libro Mayor. 

#### **Pantallas del caso** 

#### **Verificación de ventas** 

- Listado con título, cantidad, precio unitario, moneda, país de origen, fecha y hora del evento. 

- Cuando estén disponibles, se muestran identificador único y componentes informados de venta, comisión, impuesto y neto. 

- El panel refleja los eventos recibidos, sus acumulados y el estado de conexión informado por la simulación. 

- Acciones del DCU: Realizar Estimación, Contabilizar Ventas, Conciliar Ventas y Conectar con API. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El servicio simulado entrega un evento. 

2. El sistema valida los datos y muestra el evento pendiente de revisión. 

3. El panel actualiza el listado y los acumulados que estén disponibles. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

4. El Contador General revisa la información. 

5. El usuario elige una acción relacionada del DCU. 

#### **Flujos Alternativos** 

- Identificador duplicado, moneda no admitida o valores inválidos: se rechaza el evento y se informa la causa. 

- No hay eventos: la lista queda vacía. 

- Servicio desconectado: se muestra el estado de conexión. 

#### **Precondiciones** 

- El Contador General inició sesión; la simulación está disponible. 

#### **Poscondiciones** 

- Las ventas recibidas quedan disponibles para revisión; aún no se registran en el Libro Mayor. 

#### **Relaciones** 

Contabilizar Ventas y Conciliar Ventas extienden este caso; Conectar con API se incluye según el DCU. 

### **CU-08.1 - Realizar Estimación** 

**Actores:** Contador de Costos 

**Prioridad / Fuente:** No indicada en el DCU | DCU; módulo de costos por órdenes de trabajo de la SRS; Modelo de Negocio 

#### **Descripción** 

Prepara una estimación de costos asociada al videojuego u orden de trabajo. La estimación es información de costos y no constituye por sí sola un movimiento contable. 

#### **Pantallas del caso** 

#### **Estimación de costos** 

- Identificación del videojuego u orden de trabajo. 

- Datos definidos en las fuentes: presupuesto de horas, horas y tarifa de mano de obra por programador, y costos indirectos aplicables. 

- El método se conserva como dato informativo y el presupuesto de horas se estima por juicio de expertos. 

- No se fija una fórmula de distribución, tarifa concreta ni aprobación no documentada. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El Contador de Costos abre Realizar Estimación. 

2. El sistema muestra videojuegos u órdenes disponibles. 

3. El contador captura el presupuesto de horas y los datos de costo disponibles. 

4. El sistema presenta la estimación asociada al videojuego. 

5. El contador revisa y guarda la información. 

#### **Flujos Alternativos** 

- No existe una orden seleccionable: no se asocia la estimación. 

- Faltan datos: se señalan sin sustituirlos por valores supuestos. 

- Falla el guardado: no se confirma la estimación. 

#### **Precondiciones** 

- El Contador de Costos tiene sesión activa; existe un videojuego u orden. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Poscondiciones** 

 La estimación queda asociada al registro de costos y no crea por sí sola un movimiento del Libro Mayor. 

#### **Relaciones** 

Caso asociado en el DCU; no se especifica una relación UML de inclusión o extensión. 

### **CU-08.2 - Contabilizar Ventas** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-021 a RF-023 para datos de venta; instrucción vigente de registro directo 

#### **Descripción** 

Registra en el Libro Mayor los valores de las ventas verificadas, usando cuentas e importes disponibles y documentados. 

#### **Pantallas del caso** 

#### **Registro de ventas en el Libro Mayor** 

- Lista de eventos verificados con título, fecha, cantidad, precio unitario, moneda y componentes informados como venta, comisión, impuesto y neto. 

- Vista de las cuentas disponibles según el mapeo contable vigente y la clasificación contractual documentada. 

- Acción Registrar en Libro Mayor y resultado por venta procesada. 

- Las tasas y reglas fiscales se usan únicamente si están verificadas y configuradas; la SRS las identifica como parámetros pendientes de validar. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. Desde Verificar Ventas, el contador selecciona ventas que desea registrar. 

2. El sistema muestra cada evento y las cuentas disponibles conforme al mapeo vigente. 

3. El contador revisa la información y solicita Registrar en Libro Mayor. 

4. El sistema valida evento, cuenta, importe y estado del período. 

5. El sistema registra directamente los valores que cuentan con tratamiento documentado. 

6. El sistema confirma el resultado y deja los datos disponibles para consulta y Estado de Resultados. 

#### **Flujos Alternativos** 

- Evento ya registrado: se evita duplicarlo y se muestra el resultado existente. 

- Datos incompletos, cuenta no disponible o período cerrado: no se registra y se indica la causa. 

- Clasificación o tratamiento fiscal sin documentar: se deja pendiente, sin suponer la regla. 

- Falla el guardado: no se confirma el registro. 

#### **Precondiciones** 

- La venta fue verificada; el contador tiene sesión activa; período y cuentas son consultables. 

#### **Poscondiciones** 

- Los valores confirmados quedan directamente en el Libro Mayor y pueden alimentar informes. 

#### **Relaciones** 

Extiende Verificar Ventas. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

### **CU-08.3 - Conciliar Ventas** 

**Actores:** Contador General 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-024 

#### **Descripción** 

Compara liquidaciones de Steam con depósitos bancarios por período, moneda y título, mostrando diferencias y elementos pendientes. 

#### **Pantallas del caso** 

#### **Conciliación de ventas** 

- Criterios: período, moneda y título. 

- Liquidaciones del reporte Steam y depósitos con fecha, importe, moneda y referencia bancaria. 

- Área para confirmar asociaciones; resultado con diferencias, liquidaciones pendientes y depósitos sin asociar. 

- El formato de liquidación Steam está pendiente en la SRS; no se fija una plantilla ni columnas adicionales. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El contador selecciona Conciliar Ventas. 

2. El sistema solicita período, moneda y título. 

3. El contador ingresa criterios y selecciona los datos bancarios respaldados. 

4. El sistema reúne liquidaciones y depósitos candidatos. 

5. El contador confirma asociaciones. 

6. El sistema presenta estado, diferencias y registros no asociados. 

#### **Flujos Alternativos** 

- Monedas distintas: no se convierten automáticamente. 

- Falta fecha, importe, moneda o referencia bancaria: se señala el dato. 

- No hay elementos candidatos: se presenta el resultado vacío. 

- Formato de reporte no definido: se informa que el insumo requiere especificación. 

#### **Precondiciones** 

- El contador tiene sesión activa; hay una liquidación y respaldo bancario disponibles. 

#### **Poscondiciones** 

- La conciliación queda visible y no modifica el Libro Mayor. 

#### **Relaciones** 

Extiende Verificar Ventas. 

### **CU-08.4 - Conectar con API** 

**Actores:** Contador General y Servicio Steam 

**Prioridad / Fuente:** No indicada en el DCU | DCU; SRS RF-021; servicio simulado 

#### **Descripción** 

Recibe eventos desde el servicio Steam simulado para que se revisen en Verificar Ventas. No representa una conexión real con Steam. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

#### **Pantallas del caso** 

#### **Interacción del servicio** 

- Las fuentes no describen una pantalla separada de configuración de API. 

- El estado de conexión y los eventos aparecen en Verificar Ventas. 

- Datos definidos para el evento: título, cantidad, precio unitario, moneda, país, fecha y hora e identificador único. 

- No se agregan credenciales, claves, URL ni parámetros de conexión no documentados. 

#### **Flujo de Eventos** 

#### **Flujo Básico** 

1. El sistema inicia la interacción simulada desde el flujo de ventas. 

2. El servicio entrega los datos del evento. 

3. El sistema valida identificador, título, cantidad, moneda e importe. 

4. Los eventos válidos se muestran en Verificar Ventas y se actualiza el estado de conexión. 

#### **Flujos Alternativos** 

- Servicio no disponible: se informa en el panel de ventas. 

- Identificador duplicado o datos inválidos: el evento se rechaza con su motivo. 

- No se reciben eventos: no se presenta una venta como recibida. 

#### **Precondiciones** 

- El servicio simulado está configurado y disponible. 

#### **Poscondiciones** 

- Los eventos válidos quedan disponibles para verificar; el registro en el Libro Mayor ocurre en Contabilizar Ventas. 

#### **Relaciones** 

Incluido por Verificar Ventas según el DCU; Servicio Steam es actor externo. 

## **Definiciones pendientes para actualizar las fuentes** 

Los siguientes detalles no están definidos para el flujo actualizado y no se han convertido en reglas de pantalla: 

- Libro Mayor: la instrucción de negocio define el registro directo. La SRS anterior describe fecha, cuenta, concepto y valores debe/haber para consulta, pero falta definir cómo se captura el importe, qué validaciones aplican y cómo se corrigen registros posteriores. 

- Balance de Comprobación: el DCU mantiene el caso, pero la SRS anterior incluye una regla de igualdad. Falta definir su presentación y criterio de revisión en el flujo actualizado. 

- Cierres y Hoja de Trabajo: el DCU conserva estos casos, mientras que los efectos descritos en la SRS no se han actualizado. Falta confirmar las acciones que cambian el estado del período y el contenido de la hoja. 

- Ventas: se conservan la simulación y los datos de liquidación documentados; la asignación a cuentas y el tratamiento fiscal solo se aplican cuando están respaldados por reglas vigentes y parámetros verificados. 

Documento de trabajo para prototipado | Sistema Contable SunGames 

