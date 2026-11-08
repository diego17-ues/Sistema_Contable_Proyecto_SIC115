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

6. Crear el archivo `.env` en la raíz, a partir de `.env.example`, con los datos de tu base local. El archivo `.env` no se sube al repositorio.

7. Aplicar las migraciones:

   ```powershell
   python manage.py migrate
   ```

8. Encender el servidor:

   ```powershell
   python manage.py runserver
   ```

   Abrir `http://127.0.0.1:8000/` en el navegador.

**Cuentas de prueba:** el proyecto no tiene usuarios por defecto. Para crear cuentas de prueba, usa `python manage.py crear_usuario_prueba` cuando esté disponible. Estas cuentas son solo para desarrollo local.

**Si `migrate` falla con `InconsistentMigrationHistory`:** la base local tiene un historial anterior al modelo de usuario actual. Recrea la base (`DROP DATABASE` y `CREATE DATABASE`) y vuelve a ejecutar `migrate`.

## 🧪 Pruebas

```powershell
python manage.py test
```

Las pruebas usan PostgreSQL y crean una base temporal, por lo que el usuario de la base debe tener `CREATEDB`. Los servicios se prueban con repositorios simulados; las pruebas de integración usan la base real.

## 📚 Documentación

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