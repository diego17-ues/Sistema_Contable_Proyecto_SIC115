# Manual de usuario

## Sistema Contable SunGames

**Acceso en producción:** [https://stellar-serenity-production-68069db3.up.railway.app/](https://stellar-serenity-production-68069db3.up.railway.app/)

Este manual explica cómo ingresar al sistema y utilizar sus módulos principales. Las opciones disponibles dependen del rol asignado a cada cuenta.

## 1. Iniciar y cerrar sesión

1. Abra el enlace de producción en un navegador actualizado.
2. Ingrese su **nombre de usuario** y contraseña. El nombre completo no sustituye al nombre de usuario.
3. Pulse **Iniciar sesión**. El sistema abrirá el panel inicial correspondiente a su rol.
4. Para salir, use **Cerrar sesión** en la parte inferior del menú lateral.

La sesión termina después de **10 minutos sin actividad**. También será necesario iniciar sesión otra vez después de que el servidor se reinicie. Si no puede ingresar, verifique el nombre de usuario y contacte al administrador para revisar que la cuenta esté activa o restablecer su contraseña.

No hay contraseñas predeterminadas compartidas por la aplicación. Las credenciales se entregan de forma privada.

## 2. Navegación y convenciones

- El menú lateral muestra únicamente los módulos habilitados para su rol.
- El encabezado identifica al usuario y su rol. El estado del período se muestra en el panel de contabilidad.
- Las fechas se presentan como día/mes/año y los importes en dólares estadounidenses (USD).
- Los filtros permiten consultar datos por cuenta, estado, texto o rango de fechas, según cada módulo.
- Las tablas pueden tener varias páginas. Use los controles al pie para cambiar de página.
- Antes de confirmar cierres, anulaciones, registros o cambios, revise los datos y la vista previa que presenta la pantalla.

## 3. Roles y módulos

| Rol | Funcionalidades principales |
|---|---|
| **Administrador** | Acceso a los módulos contables, de ventas y de costos; administración de usuarios; auditoría; mantenimiento del catálogo de cuentas. Es el único rol que puede reabrir un período cerrado provisionalmente. |
| **Contador General** | Dashboard, Libro Mayor, consulta del catálogo de cuentas, ventas y conciliación, estados financieros y cierre provisional. Puede cerrar un período, pero no reabrirlo. |
| **Contador de Costos** | Dashboard de costos, estimaciones, órdenes de trabajo, costos indirectos y rendimiento de videojuegos. No tiene acceso a las pantallas operativas de ventas. |

El Administrador comienza en **Usuarios**. Puede ir a **Dashboard** y acceder a los demás módulos desde el menú lateral.

## 4. Dashboard

### Contador General y Administrador

El dashboard presenta indicadores de ventas recibidas y registradas para el período seleccionado, ventas pendientes, actividad reciente y resumen de órdenes de trabajo finalizadas. Puede cambiar entre los últimos 30 días, los últimos 90 días o el año actual.

### Contador de Costos

El dashboard está centrado en las operaciones de costos. Muestra órdenes pendientes y finalizadas, la última orden registrada, el rendimiento de la última orden finalizada y comparaciones recientes entre estimación y costo real.

Los indicadores se calculan con los registros disponibles en la base de datos. Si todavía no existen órdenes finalizadas o estimaciones vinculadas, algunos importes o comparaciones aparecerán como “—”.

## 5. Funciones del Contador General

### 5.1 Libro Mayor

1. Abra **Libro Mayor**.
2. Seleccione la cuenta y, si desea, las fechas inicial y final.
3. Pulse **Consultar** para ver los movimientos y el saldo.
4. Para registrar, elija la cuenta, capture fecha, descripción, referencia e importes en las líneas de la transacción, y pulse **Guardar en Libro Mayor**.
5. Para agregar una línea, use **Agregar línea**. Revise los datos y corrija cualquier error señalado antes de guardar.

El registro se realiza directamente en el Libro Mayor. Cada movimiento se conserva con su fecha y cuenta.

### 5.2 Balance de comprobación

Desde **Libro Mayor**, abra **Balance de comprobación**, indique la fecha de corte y pulse **Generar**. Puede descargar el informe en PDF o Excel. Si aparece una diferencia entre Debe y Haber, revise las cuentas y movimientos registrados.

### 5.3 Catálogo de cuentas

El Contador General puede buscar y consultar cuentas, pero no registrarlas ni modificarlas. Use los filtros por código, denominación o clasificación y abra **Consultar** para ver los datos de una cuenta.

### 5.4 Ventas

- **Verificar ventas:** consulte las ventas recibidas, filtre por fechas o texto y revise el estado, origen, producto e importe. El origen identifica si la venta es real o simulada.
- **Contabilizar ventas:** revise las ventas pendientes y use **Registrar** para incorporarlas al Libro Mayor.
- **Conciliar ventas:** indique el rango de fechas y pulse **Calcular período**. Revise el total y la tabla de cuentas afectadas, incluidos Debe y Haber. Si los datos son correctos, pulse **Confirmar y contabilizar**.
- **Conexión Steam:** consulte el estado de conexión y, si es necesario, ejecute un ciclo manual con **Ejecutar ciclo**.

El simulador integrado genera ventas de ejemplo automáticamente, con origen **Simulada**. Ejecuta ciclos cada cinco minutos y omite el ciclo si se recibió una venta real en los cinco minutos anteriores. Las ventas simuladas deben tratarse como datos de demostración, no como ingresos reales.

### 5.5 Estados financieros y cierre provisional

Los estados financieros disponibles incluyen Estado de Resultados, Estado de Situación Financiera y Estado de Cambios en el Patrimonio. Se pueden consultar y descargar desde las pestañas correspondientes.

Para preparar un cierre provisional cuando el período está abierto:

1. Abra **Estados financieros → Cierre provisional**.
2. Seleccione las fechas y pulse **Consultar requisitos**.
3. Registre en el Libro Mayor las ventas que sigan pendientes y confirme que existan movimientos para el rango.
4. Genere y revise la **Hoja de trabajo**.
5. Si las validaciones están completas, confirme el cierre provisional.

Mientras el cierre provisional esté activo, el sistema muestra los documentos generados para consulta y no ofrece generarlos nuevamente como si el período estuviera abierto. El período cerrado no admite nuevos movimientos con fechas dentro de ese rango. El Contador General puede consultar el cierre, pero solo el Administrador puede reabrirlo.

## 6. Funciones del Contador de Costos

### 6.1 Estimaciones

1. Abra **Estimación** y registre el videojuego si aún no aparece en la lista.
2. Abra el juego para consultar fases, estimaciones y versiones de presupuesto.
3. Registre o revise estimaciones por fase con los datos de rol, experto y valores solicitados en el formulario.
4. Consulte la consolidación y las versiones del presupuesto. Las acciones disponibles —por ejemplo, aprobar, rechazar o restaurar— aparecen según el estado de la versión.
5. Mantenga actualizados los parámetros y catálogos de costos desde **Parámetros y catálogos**.

### 6.2 Órdenes de trabajo y hoja de costos

1. Abra **Costeo Videojuego → Nueva orden**.
2. Indique el juego, la fecha de inicio y, cuando corresponda, la estimación de referencia.
3. En la hoja de costos de la orden, registre mano de obra directa, costos directos y costos indirectos. Complete también las licencias estimadas para obtener el costo unitario estimado.
4. Revise los subtotales y el resumen por proceso. Puede anular un registro vigente; el sistema conserva el registro y muestra su estado como anulado.
5. Cuando la orden esté completa, use **Finalizar orden** y confirme la acción.

Al registrar mano de obra directa, las retenciones del empleado y cargas patronales configuradas se calculan y contabilizan automáticamente; este flujo no es un módulo de nómina. Los costos de una orden en proceso permanecen como videojuegos en proceso (cuenta 1106). Al finalizarla, sus saldos se trasladan a videojuegos terminados (cuenta 1107).

Las órdenes se pueden editar, archivar y restaurar desde el listado, según su estado. Archivar una orden conserva su historial y sus registros contables.

### 6.3 Costos indirectos

1. Abra **Indirectos del período** y seleccione un período.
2. Revise el pool elegible, las fuentes, tasas, alertas y distribución por orden.
3. Si el período está abierto y la vista previa es correcta, aplique los indirectos.
4. Si necesita revertir una aplicación, revise la vista previa de reversión y confirme. Las reversiones conservan el historial contable.

Las cuentas y fuentes utilizadas se configuran desde **Catálogos**. Si el sistema indica que falta una cuenta configurada, solicite al administrador que revise esos catálogos antes de continuar.

### 6.4 Rendimiento

En **Rendimiento de videojuegos**, compare por orden el presupuesto estimado con el costo real vigente. La variación se calcula como **costo real menos estimación**: un valor positivo indica que el costo real superó el presupuesto; uno negativo indica que quedó por debajo. La pantalla muestra también la variación porcentual y la viabilidad presupuestaria cuando existe información suficiente.

## 7. Funciones del Administrador

### 7.1 Usuarios

En **Usuarios** puede consultar las cuentas existentes, crear usuarios, cambiar contraseñas, desactivar cuentas y reactivarlas. Al crear una cuenta, asigne el rol de acuerdo con las funciones que desempeñará. Desactivar una cuenta impide su acceso, pero conserva el historial.

### 7.2 Auditoría

En **Auditoría** consulte la fecha y hora, usuario que ejecutó la acción, usuario afectado, acción, resultado y detalle. Use **PDF** o **Excel** para descargar el registro.

### 7.3 Catálogo de cuentas y reapertura de períodos

El Administrador puede consultar, registrar y modificar cuentas contables desde **Catálogo de cuentas**. El código lo asigna el sistema; no se debe inventar ni reutilizar manualmente.

Para reabrir un período provisionalmente cerrado, abra **Estados financieros → Cierre contable**, seleccione la acción de reapertura y confirme. Al reabrirlo, el período vuelve a admitir operaciones; los traslados provisionales de costos regresan a sus cuentas de origen. La reapertura queda registrada en auditoría.

## 8. Recomendaciones

- Registre cada operación en la cuenta y fecha correctas. Verifique los importes antes de confirmar.
- Revise las vistas previas de conciliación, costos indirectos y cierres antes de contabilizar o cerrar.
- No comparta contraseñas ni use cuentas de otras personas.
- Para un error de acceso, un usuario inactivo o una opción que no aparece, contacte al Administrador del sistema.
- Si hay un período cerrado provisionalmente, consulte primero la Hoja de trabajo y los estados financieros generados. No intente registrar movimientos dentro de ese rango hasta que el Administrador lo reabra.

