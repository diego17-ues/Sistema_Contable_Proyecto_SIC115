### Requerimientos Ajustados para Contabilidad General de SunGames S.A. de C.V.

#### 1. Requerimientos Generales
**RG-01.** Marco normativo: Permitir seleccionar las Normas Internacionales de Información Financiera (NIIF) para PYMES como el marco referencial para la contabilidad.

**RG-02.** Plan de cuentas: Administrar un catálogo de cuentas de activos, pasivos, patrimonio y demás cuentas principales, alineado con el Manual de Aplicación del Catálogo de Cuentas de SunGames.

**RG-03.** Período contable: Crear un solo período contable para efectos de ejemplo y alineación con los requerimientos contables.

**RG-04.** Parámetros contables: Definir períodos mensuales y anuales y controlar su estado, permitiendo ajustes según las normas vigentes.

**RG-05.** Permisos de usuario: Establecer perfiles claros (administrador, contador, consulta) con permisos diferenciados, en línea con el control interno y las normativas vigentes.

#### 2. Registro y Control de Operaciones
**RCO-01.** Partida doble: Validar que todo comprobante tenga débitos iguales a créditos. Prohibir el registro de una partida no cuadrada.

**RCO-02.** Validaciones: Bloquear el uso de cuentas inactivas y períodos cerrados; validar montos para asegurar la integridad de los registros.

**RCO-03.** Tipos de partida: Permitir crear partidas dobles, de ajuste y de inicio de período, utilizando partidas para corregir errores ya registrados.

**RCO-04.** Libros contables: Crear libros contables obligatorios con base en la normativa NIIF sección 2, garantizando su integridad.

**RCO-05.** Ciclo de vida de partidas: Las partidas pueden iniciar como borradores y luego contabilizarse. Una vez contabilizadas, no se pueden editar.

**RCO-06.** Soportes: Asociar cada partida doble a un documento de respaldo, como una factura o un comprobante de ingreso.

**RCO-07.** Registrar depreciación: Registrar activos y generar la depreciación mensual en línea recta, conforme a la política contable.

**RCO-08.** Manejo de Cuentas T: Generar cuentas T que muestren los flujos de efectivo de manera automática.

**RCO-09.** Mayorización: Mostrar un estado de mayorización integral que mantenga la coherencia en la ecuación contable.

#### 3. Contabilidad de Costos
**RCC-01.** Administrar el catálogo de videojuegos mediante activos intangibles (según NIC 38 y ASC 985-20), incluyendo la capitalización y amortización automática.

**RCC-02.** Centros de costo: Definir áreas de programación, arte, diseño y control de calidad, así como los gastos de administración.

**RCC-03.** Clasificación de costos: Clasificar automáticamente cada costo como directo o indirecto.

**RCC-04.** Costo total: Calcular el costo total de cada videojuego mediante el método de órdenes de trabajo.

**RCC-05.** Reportes de costos: Consultar costos por proyecto, por centro de costo y por período.

**RCC-06.** Videojuegos en desarrollo: Acumular los costos de cada videojuego en cualquier momento y presentar su total.

#### 4. Catálogo de Videojuegos y Licencias
**RCV-01.** Registro de videojuegos: Registrar cada videojuego y llevar trazabilidad en su ciclo de desarrollo y fecha de lanzamiento.

**RCV-02.** Compras de videojuegos: Registrar datos sobre cada compra de un videojuego y generar comprobantes correspondientes.

**RCV-03.** Amortización: Automatizar la creación de amortización por cada videojuego, calculando su vida útil de acuerdo a las políticas establecidas.

**RCV-04.** Devoluciones y reembolsos: Revertir la venta y reingresar la licencia cuando corresponda.

#### 5. Estados Financieros y Control
**REF-01.** Generar estados financieros: Generar estados financieros obligatorios conforme a las NIIF, garantizando integridad y coherencia.

**REF-02.** Otros estados: Crear estados de comprobación y hojas de trabajo que apoyen al contador en su trabajo.

**REF-03.** Cierre contable: Cerrar con éxito un período contable, bloqueando su edición después del cierre.

**REF-04.** Trazabilidad y bitácora: Ofrecer un sistema que mantenga trazabilidad de la información y permita auditorías eficientes.

#### 6. Continuidad del Producto
**RCP-01.** Evolución del sistema: El sistema debe poder evolucionar para incluir otras ramas de contabilidad, como la contabilidad financiera o auditoría forense.

**RCP-02.** Implante de buenas prácticas: Implementar diversas prácticas y políticas contables para la presentación de estados financieros que mantengan fidelidad y seguridad en la gestión de documentos.

**RCP-03.** Hojas de trabajo: Crear hojas de trabajo que faciliten la gestión de cierres contables en cualquier momento de manera automática.

---

### Bitácora de Cambios

| ID Original | Estado       | Motivo                                                                                |
|-------------|--------------|---------------------------------------------------------------------------------------|
| RF-01       | CONSERVADO   | Alineado con el requerimiento general de marco normativo.                           |
| RF-02       | CONSERVADO   | Se mantiene el requerimiento de administrar un catálogo de cuentas.                  |
| RF-03       | CONSERVADO   | Se alinea con la creación del período contable para ejemplos.                       |
| RF-04       | CONSERVADO   | Control de períodos está presente en la normativa y requirió mapeo.                 |
| RF-05       | MODIFICADO   | Se agregó detalle sobre permisos diferenciados y alineación al control interno.      |
| RF-06       | MODIFICADO   | Se optimizó para especificar los tipos de partida e inclusión de correcciones.      |
| RF-07       | MODIFICADO   | Se amplió para incluir el registro de depreciación mensual conforme a la política.   |
| RF-08       | MODIFICADO   | Se ajustó para incluir la generación automática de cuentas T.                        |
| RF-09       | MODIFICADO   | Se amplió para requerir un estado de mayorización integral.                          |
| RF-10       | CONSERVADO   | Se mantiene la validación de cuentas y períodos.                                    |
| RF-11       | CONSERVADO   | Registro de soportes sigue vigente.                                                  |
| RF-12       | CONSERVADO   | Registro de depreciación en línea recta está alineado con política de la empresa.    |
| RF-13       | CONSERVADO   | Se mantiene la trazabilidad de los asientos.                                       |
| RF-14       | ELIMINADO    | El requerimiento se fusionó con RG-05 y se ajustó a un solo permiso de usuario.    |
| RF-15       | CONSERVADO   | Alineado con el sistema de activos intangibles.                                     |
| RF-16       | CONSERVADO   | Se mantiene para definir centros de costo.                                          |
| RF-17       | CONSERVADO   | Se conserva la clasificación de costos.                                              |
| RF-18       | CONSERVADO   | Calculo de costo por orden de trabajo se mantiene.                                   |
| RF-19       | CONSERVADO   | Reportes de costos son necesarios.                                                  |
| RF-20       | CONSERVADO   | Se mantiene la acumulación para videojuegos en desarrollo.                           |
| RF-21       | CONSERVADO   | Registro y trazabilidad de videojuegos es fundamental.                               |
| RF-22       | CONSERVADO   | Se mantiene el registro de compras.                                                  |
| RF-23       | CONSERVADO   | Se refiere a la amortización automatizada.                                          |
| RF-24       | CONSERVADO   | Se mantiene para la gestión de devoluciones.                                         |
| RF-25       | CONSERVADO   | Generación de estados financieros alineada con NIIF.                                 |
| RF-26       | MODIFICADO   | Hojas de trabajo precisan mayor alineación con los sistemas.                        |
| RF-27       | CONSERVADO   | Cierre contable se mantiene para el sistema.                                        |
| RF-28       | MODIFICADO   | Se refuerza la trazabilidad y bitácora por el uso contable.                        |
| RF-29       | CONSERVADO   | Evolución del sistema se mantiene.                                                  |
| RF-30       | CONSERVADO   | Membresías de buenas prácticas queda bien definido.                                  |
| RF-31       | CONSERVADO   | Se mantiene la creación de hojas de trabajo.                                        |

Este diseño cuadro permite una visualización clara del estado de cada requerimiento y así también permite a cualquier interesado identificar los cambios en la propuesta de requerimientos de forma rápida y efectiva.