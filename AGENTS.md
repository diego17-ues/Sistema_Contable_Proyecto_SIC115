# AGENTS.md: Sistema Contable SunGames (SIC115)

Este archivo define las reglas para cualquier agente o colaborador que modifique este repositorio. El detalle de cada caso de uso está en `docs/Especificación_de_Casos_de_Uso_-_DCU_Extendido.md`. Si este archivo y la especificación no coinciden, la especificación manda y hay que reportar la diferencia en el PR.

## Stack

- Python con Django y PostgreSQL. No usar Laravel, Filament, Supabase ni SQLite en el proyecto.
- Templates de Django con HTML y CSS sencillos. No introducir frameworks de frontend.
- Código conforme a PEP 8.
- Dependencias fijas en `requirements.txt`. No agregar paquetes sin justificarlo en el PR.
## Arquitectura

El código sigue una arquitectura en capas. Cada capa tiene una responsabilidad y no invade la de otra.

**Capas:**

1. **Presentación** (`views`, templates, `forms`): recibe la petición, valida el formato de los datos de entrada con formularios de Django y llama a un servicio. No contiene reglas de negocio ni consultas directas a la base.
2. **Servicios** (`services.py` en cada app): contienen la lógica de negocio y los casos de uso. Son la única puerta para crear, modificar o desactivar datos contables y de usuarios. Un servicio recibe datos ya validados y devuelve un resultado o lanza una excepción de dominio.
3. **Repositorios** (`repositories.py`): encapsulan las consultas al ORM. Los servicios piden datos al repositorio; no escriben consultas `filter()` o `objects.` directamente en su lógica.
4. **Modelos** (`models.py`): describen la estructura de los datos y sus restricciones de integridad (claves, `unique`, `CheckConstraint`). No contienen reglas de negocio complejas ni llaman a otros servicios en `save()`.

**Flujo obligatorio:** vista → formulario → servicio → repositorio → modelo.

**Principios SOLID aplicados:**

- **Responsabilidad única:** cada clase o módulo hace una sola cosa. Un servicio de cuentas no genera reportes; un exportador no valida datos de usuario.
- **Abierto/cerrado:** agregar un formato de reporte o una regla de validación no debe obligar a modificar código existente. Usar nuevas clases que implementen una interfaz común.
- **Sustitución de Liskov:** cualquier implementación de una interfaz de repositorio o exportador debe poder reemplazar a otra sin cambiar el comportamiento que espera el servicio.
- **Segregación de interfaces:** las interfaces son pequeñas y específicas. Un repositorio de bitácora no expone métodos de cuentas.
- **Inversión de dependencias:** los servicios reciben sus dependencias (repositorios, exportadores, servicio de bitácora) por el constructor. No las instancian internamente ni importan módulos concretos de persistencia.

**Patrones de diseño recomendados:**

- **Servicio (Service Layer):** un servicio por caso de uso o grupo cohesivo (`UsuarioService`, `CatalogoCuentasService`, `LibroMayorService`, `AuditoriaService`).
- **Repositorio:** una clase por agregado que centraliza las consultas. Permite probar los servicios sin base de datos.
- **Estrategia:** para formatos de exportación. `ExportadorPDF` y `ExportadorExcel` implementan la misma interfaz `Exportador`, y el servicio de auditoría recibe la estrategia que corresponda.
- **Fábrica:** para crear la estrategia de exportación según el formato solicitado.
- **Excepciones de dominio:** definir excepciones propias (`CuentaDuplicadaError`, `PeriodoCerradoError`, `UsuarioInactivoError`, `RolNoAutorizadoError`). Las vistas las traducen en mensajes para el usuario. No usar excepciones genéricas ni devolver `None` para indicar error.
- **Inyección de dependencias:** configurar las dependencias en un único punto (por ejemplo, un módulo de composición o `apps.py`), no dentro de cada vista.

**Reglas de implementación:**

- No usar `signals` de Django para lógica contable o de auditoría. Las acciones que deben registrarse en la bitácora se llaman explícitamente desde el servicio, para que el flujo sea visible y probable.
- Toda operación que modifique datos debe ejecutarse dentro de `transaction.atomic()` cuando involucre más de un registro.
- Las vistas no usan `request.user` para decidir permisos de negocio directamente. Los permisos se validan en el servicio con el rol del usuario, y la vista solo muestra o bloquea opciones de menú.
- Evitar sobreingeniería: no crear interfaces ni repositorios para cosas que tienen una sola implementación y no tienen una razón clara para cambiar. Justificar cada abstracción nueva en el PR.
- Las funciones de servicio no superan una responsabilidad clara. Si un método hace validación, cálculo y persistencia a la vez, dividirlo en métodos privados o en colaboradores.
- Cada servicio tiene pruebas unitarias con repositorios simulados (mocks o implementaciones en memoria), además de pruebas de integración contra PostgreSQL para las consultas reales.

## Alcance de la entrega actual

Implementar únicamente los casos indicados aquí. Todo lo demás queda fuera.

**Administrador:**
- CU-01 Iniciar sesión (compartido por todos los roles)
- CU-02 Administrar Usuarios, con CU-02.1 Agregar, CU-02.2 Desactivar y CU-02.3 Consultar
- CU-03 Control de Auditoría, con CU-03.1 Consultar Logs, CU-03.2 Descargar Logs, CU-03.2.1 Descargar PDF y CU-03.2.2 Descargar Excel

**Contador General:**
- CU-04 Generar Libro, con CU-04.1 Crear Balance de Comprobación y CU-04.2 Consultar Libro
- CU-05 Libro Mayor, con CU-05.1 Consultar Saldo de Cuentas
- CU-06 Catálogo de Cuentas, con CU-06.1 Registrar, CU-06.2 Eliminar y CU-06.3 Modificar
- CU-07 Estados Financieros, con CU-07.1 Cierre Contable, CU-07.2 Cierre Provisional, CU-07.2.1 Hoja de Trabajo, CU-07.3 Cierre Anual, CU-07.4 Estado de Cambios en el Patrimonio, CU-07.5 Estado de Resultados y CU-07.6 Balance General
- CU-08 Verificar Ventas, con CU-08.2 Contabilizar Ventas, CU-08.3 Conciliar Ventas y CU-08.4 Conectar con API (servicio Steam simulado)

**Diferido (no implementar):**
- CU-08.1 Realizar Estimación y todo el sistema de costos. Se definirá más adelante.
- El rol Contador de Costos. No debe aparecer en menús, formularios ni listas de roles.

## Reglas contables

- El registro contable se hace **directamente en el Libro Mayor**, según la instrucción vigente de negocio. No crear un libro diario ni un flujo de partida doble.
- Los valores de ventas solo se registran en el Libro Mayor cuando el evento está verificado y tiene un tratamiento documentado.
- Un período cerrado no admite nuevos registros para sus fechas.
- Las tasas e impuestos se usan solo si están verificados y configurados como parámetros. No fijarlos en el código.
- Mobiliario y equipo se capitaliza a partir de USD 500.
- El Balance de Comprobación no se bloquea por desigualdad entre columnas debe y haber.
- Código de cuenta de 4 dígitos: posición 1 rubro, posición 2 naturaleza, posiciones 3 y 4 número de cuenta dentro del grupo (01 a 99). El código lo asigna el servicio, nunca el usuario. Un código dado de baja no se reutiliza.

## Eliminaciones

- Las cuentas se dan de baja de forma **lógica**, según RF-008. Nunca borrar físicamente una cuenta ni un registro del Libro Mayor.
- Los usuarios se desactivan cambiando su estado a inactivo. El registro y su historial se conservan.

## Seguridad y acceso

- Las credenciales no se muestran en mensajes de error. Ante un fallo de login, el mensaje es general.
- Una cuenta inactiva o bloqueada no puede iniciar sesión.
- Cada rol ve solo las opciones de su menú. Un acceso fuera de rol se bloquea en el servidor, no solo en el menú.
- Todo cambio de usuario, cuenta contable o estado de período, y cada intento de inicio de sesión, se registra en la bitácora.
- No subir `.env`, contraseñas ni claves al repositorio.

## Pendiente de definir: no implementar sin confirmación

Si una tarea depende de alguno de estos puntos, no inventar la regla. Dejar un `TODO` con el número de caso y reportarlo en el PR.

- **Contraseña de usuarios nuevos:** cómo se establece al crear una cuenta (CU-02.1).
- **Captura de importes en el Libro Mayor:** campos, validaciones y forma de corregir registros posteriores (CU-05).
- **Cierres y Hoja de Trabajo:** acciones que cambian el estado del período y contenido de la hoja (CU-07).
- **Formato de liquidación de Steam** para la conciliación (CU-08.3).
- **Nombre de archivo y plantilla** de los reportes PDF y Excel de auditoría (CU-03.2).
- **Tratamiento fiscal** de las ventas y tasas aplicables.

## Interfaz

- Idioma español. Fechas en formato día/mes/año. Importes en USD con dos decimales.
- Encabezado con nombre del usuario y rol, menú con las opciones autorizadas y área principal.
- Los campos obligatorios se identifican. Los errores aparecen junto al campo y se conservan los demás valores válidos.
- Los listados se paginan cuando el volumen lo requiere.
- Las acciones que modifican datos piden confirmación explícita.
- Usar los templates existentes del contador como base. Las pantallas nuevas del administrador siguen el mismo layout y no se crean pantallas fuera de la especificación.

## Ejecución local

1. Copiar `.env.example` a `.env` y completar los valores.
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `python manage.py test`

Los pasos completos de instalación están en `README.md`.

## Entregables de cada tarea

- Código, migraciones y pruebas para la lógica nueva.
- Pruebas para los casos de error y los flujos alternativos del caso de uso.
- Descripción en el PR con los casos cubiertos (CU-xx), los pendientes dejados como TODO y cualquier diferencia con la especificación.
- Las migraciones aplicadas no se modifican. Cualquier cambio de esquema se hace con una migración nueva.

## Prohibiciones

- No modificar la especificación para ajustarla al código. Si hay conflicto, se reporta.
- No agregar funciones de costos, estimaciones ni roles diferidos.
- No trabajar directamente en `main`.
- No poner lógica de negocio en vistas, templates, formularios ni señales de Django.

**Administrador:**
- CU-01 Iniciar sesión (compartido por todos los roles)
- CU-02 Administrar Usuarios, con CU-02.1, CU-02.2 y CU-02.3
- CU-03 Control de Auditoría, con CU-03.1, CU-03.2, CU-03.2.1 y CU-03.2.2
- CU-06 Catálogo de Cuentas: consulta, registro, modificación y baja. Excepción a la especificación, que asigna registro y modificación al Contador General.

**Contador General:**
- CU-04, CU-05, CU-07, CU-08 (con sus subcasos)
- CU-06 Catálogo de Cuentas: solo consulta.

El registro contable es por movimiento: cada movimiento tiene una cuenta, un importe firmado y una fecha. El sistema no exige que una transacción cuadre al registrarla. El cuadre se verifica en el Balance de comprobación (CU-04.1), y el contador es responsable de registrar completas las transacciones. Ningún movimiento se guarda si sus datos no son válidos.