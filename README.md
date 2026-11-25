<p align="center">
  <img src="static/sic_sunGames/SunGames_Logop.ng" alt="Logo de SunGames S.A de C.V." width="200">
</p>
# 📊 Sistema Contable SunGames S.A de C.V.

Sistema de contabilidad general y de costospara una empresa desarrolladora de videojuegos que comercializa sus productos mediante licencias. Desarrollado bajo la normativa contable y mercantil de El Salvador.

---

## 📌 Tabla de contenido

- [Descripción](#-descripción)
- [Alcance](#-alcance)
- [Tecnologías](#-tecnologías)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Requisitos previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Pruebas](#-pruebas)
- [Documentación](#-documentación)
- [Equipo](#-equipo)
- [Licencia](#-licencia)

---

## 📖 Descripción

**SunGames** es la empresa ficticia que sirve de caso de estudio: desarrolla videojuegos y obtiene sus ingresos principalmente de la **venta de licencias**. El sistema registra las operaciones contables de la empresa, desde el catálogo de cuentas hasta la generación de estados financieros.

## 🧭 Alcance

| Módulo | Casos de uso | Estado |
|--------|--------------|--------|
| Inicio de sesión | CU-01 | En desarrollo |
| Administración de usuarios | CU-02 | En desarrollo |
| Auditoría (bitácora) | CU-03 | En desarrollo |
| Catálogo de cuentas | CU-06 | Pendiente |
| Libro Mayor y saldos | CU-04, CU-05 | Pendiente |
| Estados financieros y cierres | CU-07 | Pendiente |
| Ventas y conciliación | CU-08 | Pendiente |
| Contabilidad de costos | CU-08.1 | Diferido |

**Roles:**

- **Administrador:** administra usuarios, consulta y descarga la auditoría, y gestiona el catálogo de cuentas.
- **Contador General:** consulta el catálogo, registra movimientos, genera el Libro Mayor, el Balance de comprobación y los estados financieros.

La contabilidad de costos está diferida hasta definir el método de la empresa.

## ⚙️ Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, Django 4.2 |
| Base de datos | PostgreSQL 18 |
| Interfaz | Plantillas de Django con HTML y CSS |
| Pruebas | Django test framework, con PostgreSQL |
| Dependencias | pip, `requirements.txt` |

## 🗂️ Estructura del proyecto

```text
├── AGENTS.md            # Reglas de desarrollo, alcance y arquitectura
├── README.md
├── requirements.txt
├── .env.example         # Variables de entorno (sin valores reales)
├── manage.py
├── docs/                # Especificación de casos de uso
├── sistema_contable_sunGames/   # Configuración del proyecto
├── usuarios/            # Inicio de sesión y usuarios (CU-01, CU-02)
├── bitacora/            # Registro y consulta de auditoría (CU-03)
├── catalogo/            # Catálogo de cuentas (CU-06)
└── libro_mayor/         # Movimientos y saldos (CU-04, CU-05)
```

Cada app sigue la misma arquitectura: vistas, formularios, servicios, repositorios, modelos y pruebas. Las reglas de negocio viven en los servicios, no en las vistas.

## ✅ Requisitos previos

- Python 3.12
- PostgreSQL 18 y pgAdmin 9.x
- Git

## 🚀 Instalación

1. Clonar el repositorio y entrar a la carpeta del proyecto.

2. Crear y activar el entorno virtual:

   ```powershell
   py -3.12 -m venv env
   .\env\Scripts\Activate.ps1
   ```

3. Instalar las dependencias:

   ```powershell
   pip install -r requirements.txt
   ```

4. Crear el usuario y la base de datos en PostgreSQL, desde pgAdmin conectado como `postgres`:

   ```sql
   CREATE USER sic115_user WITH PASSWORD '<clave_local>';
   ALTER USER sic115_user CREATEDB;
   CREATE DATABASE sic115_db OWNER sic115_user;
   ```

   `CREATEDB` es necesario para que las pruebas creen su base temporal.

5. Conectar a `sic115_db` y dar permisos sobre el esquema:

   ```sql
   GRANT ALL ON SCHEMA public TO sic115_user;
   ```

6. Entrar a `app/sistema_contable_sunGames` y crear ahí el archivo `.env`, a partir de `.env.example`. Reemplaza los valores de ejemplo de base de datos, `SECRET_KEY` y tokens por valores propios. El archivo `.env` no se sube al repositorio.

7. Aplicar las migraciones:

   ```powershell
   python manage.py migrate
   ```

8. Iniciar la interfaz y el simulador en segundo plano con un comando:

   ```powershell
   python manage.py iniciar_sistema
   ```

   Abre `http://127.0.0.1:8000/`. Cada inicio del servidor invalida las
   sesiones anteriores. Si el servidor se reinicia, inicia sesión de nuevo.
   No hay credenciales predeterminadas; utiliza una cuenta ya provisionada.
   El administrador puede crear usuarios de prueba desde **Usuarios**.

**Cuentas de prueba:** el proyecto no trae usuarios ni contraseñas por defecto. En una instalación con administrador provisionado, crea usuarios desde **Usuarios**; en una base nueva, primero debe aprovisionarse la cuenta administradora.

**Si `migrate` falla con `InconsistentMigrationHistory`:** la base local tiene un historial anterior al modelo de usuario actual. Recrea la base (`DROP DATABASE` y `CREATE DATABASE`) y vuelve a ejecutar `migrate`.

## Simulador de ventas Steam

El panel **Ventas → Conexión Steam** permite consultar el estado y ejecutar un
ciclo manual. El comando `iniciar_sistema` arranca la interfaz web y un proceso
que ejecuta el simulador al iniciar y luego cada 24 horas. Se usa un comando
de Django con espera en bucle: el repositorio no incluye Docker Compose ni
requiere servicios externos como Redis.

El ciclo reutiliza el generador y el envío HTTP de `simulador_steam`. Cada ciclo
envía como máximo una venta aleatoria de su catálogo; no depende de las órdenes
de costos ni de títulos registrados. Si se recibió una venta con origen **Real**
en los últimos cinco minutos, el ciclo se omite. Las ventas nuevas quedan
marcadas como **Simuladas** y usan el mismo identificador `SIM-` durante todos
los reintentos de la solicitud.

Variables disponibles en `app/sistema_contable_sunGames/.env.example`:

| Variable | Uso | Valor predeterminado |
|---|---|---|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Base PostgreSQL y credenciales. | Sin valor; requeridas |
| `DB_HOST`, `DB_PORT` | Conexión PostgreSQL. | `localhost`, `5432` |
| `SECRET_KEY` | Firma de sesión Django. | Sin valor; requerida |
| `DEBUG` | Modo de depuración. | `False` |
| `STEAM_WEBHOOK_TOKEN` | Autentica los eventos enviados al sistema contable. | Sin valor; requerido |
| `SIMULATOR_CRON_TOKEN` | Protege el disparo desde cron externo. | Sin valor; endpoint deshabilitado |
| `SIMULATOR_ACCOUNTING_URL` | URL base del sistema contable. | `http://127.0.0.1:8000` |
| `SIMULATOR_INTERVAL_SECONDS` | Intervalo del proceso local. | `86400` (24 horas) |
| `SIMULATOR_REAL_SALE_WINDOW_SECONDS` | Ventana de pausa por ventas reales. | `300` |
| `SIMULATOR_API_TIMEOUT_SECONDS` | Timeout de cada llamada HTTP. | `10` |
| `SIMULATOR_MAX_RETRIES` | Reintentos adicionales para red o errores 5xx. | `2` |
| `SIMULATOR_WEB_BIND` | Host y puerto para `iniciar_sistema`. | `127.0.0.1:8000` |
| `ALLOWED_HOSTS` | Hosts aceptados por Django, separados por coma. | `127.0.0.1,localhost,testserver` |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS adicionales, separados por coma. | Sin valor |

Para cambiar la frecuencia, ajusta `SIMULATOR_INTERVAL_SECONDS` y reinicia
`iniciar_sistema`. Cada ciclo comparte un bloqueo PostgreSQL para evitar
ejecuciones simultáneas. El endpoint protegido permite hacer
`POST /api/steam/simular/` con el header
`Authorization: Bearer <SIMULATOR_CRON_TOKEN>` desde un cron externo, si se
necesita.

### Despliegue integrado en Railway

La aplicación y el scheduler se ejecutan en un mismo servicio. Railway debe
usar `app/sistema_contable_sunGames` como **Root Directory**. En la configuración
del servicio define estos comandos:

| Configuración | Comando |
|---|---|
| Build | `python manage.py collectstatic --noinput` |
| Pre-deploy | `python manage.py migrate` |
| Start | `python manage.py iniciar_sistema --railway` |

Agrega PostgreSQL al proyecto Railway y vincula al servicio web las variables
`PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST` y `PGPORT` que proporciona la base.
El proyecto las reconoce directamente. Configura además `SECRET_KEY` con un
secreto generado para el despliegue, `DEBUG=False`, `STEAM_WEBHOOK_TOKEN`,
`SIMULATOR_CRON_TOKEN` y, si se desea cambiar el intervalo, `SIMULATOR_INTERVAL_SECONDS`
(por defecto `86400`, 24 horas). Railway proporciona `PORT` y `RAILWAY_PUBLIC_DOMAIN`; el
arranque enlaza Gunicorn a ese puerto, y Django acepta el dominio asignado y lo
usa como origen CSRF predeterminado. Deja `SIMULATOR_ACCOUNTING_URL` sin definir:
el scheduler enviará las ventas al servidor web de este mismo servicio.

Tras guardar estos ajustes, Railway construye los estáticos, aplica migraciones
antes del despliegue y arranca Gunicorn junto al proceso `simular_ventas --continuo`.
El supervisor detiene ambos procesos cuando Railway reinicia o apaga el servicio.
Al arrancar se invalidan las sesiones anteriores para solicitar autenticación
nuevamente. La URL pública y las cuentas de prueba se obtienen desde Railway y
la base aprovisionada; este repositorio no incluye credenciales predeterminadas.
En **Settings → Networking**, genera el dominio público del servicio. Mantén una
sola réplica de la aplicación para que haya un único proceso scheduler.

## 🧪 Pruebas

```powershell
python manage.py test
```

Las pruebas usan PostgreSQL y crean una base temporal, por lo que el usuario de la base debe tener `CREATEDB`. Los servicios se prueban con repositorios simulados; las pruebas de integración usan la base real.

## 📚 Documentación

- [`Manual de usuario`](app/sistema_contable_sunGames/docs/manual_usuario.md): guía de acceso, roles, contabilidad, ventas, costos y cierres.
- [`AGENTS.md`](AGENTS.md): reglas de desarrollo, alcance y arquitectura.
- [`docs/Especificación_de_Casos_de_Uso_-_DCU_Extendido.md`](docs/Especificación_de_Casos_de_Uso_-_DCU_Extendido.md): casos de uso y su alcance.

## 👥 Equipo

| Integrante | Rol |
|-----------|-----|
| Diego | Líder del proyecto |
| David Alexander Rivas Rivas | Desarrollo |
| Josué Nehemias Renderos Hernández | Desarrollo |

## 📄 Licencia

Proyecto elaborado con fines académicos. SunGames S.A de C.V. es una empresa ficticia y todas sus operaciones son simuladas.
