# Sistema_Contable_Proyecto_SIC115
## Aplicación de los conceptos de la cátedra de SIC115 en la Universidad de El Salvador
# 📊 Sistema Contable SunGames S.A de C.V.

Sistema de contabilidad general y de costos para una empresa desarrolladora de videojuegos que comercializa sus productos mediante licencias. Desarrollado bajo la normativa contable y mercantil de El Salvador.
---

## 📌 Tabla de contenido

- [Descripción](#-descripción)
- [Características](#-características)
- [Tecnologías](#-tecnologías)
- [Requisitos previos](#-requisitos-previos)
- [Equipo](#-equipo)
- [Licencia](#-licencia)
---

## 📖 Descripción

**SunGames** es la empresa ficticia que sirve de caso de estudio: desarrolla videojuegos y obtiene sus ingresos principalmente de la **venta de licencias**. El sistema automatiza el registro contable de sus operaciones, desde el catálogo de cuentas hasta la generación de estados financieros, respetando el método de **partida doble**.

El alcance se centra en **contabilidad general** y **contabilidad de costos**, incluyendo el control de inventario y el catálogo de productos.

## ✨ Características

- **Catálogo de cuentas** — estructura jerárquica adaptada a una empresa de videojuegos.
- **Libro diario** — registro cronológico de partidas contables.
- **Libro mayor** — mayorización automática por cuenta.
- **Motor de partida doble** — valida que el debe y el haber siempre cuadren.
- **Catálogo de productos** — videojuegos y licencias comercializadas.
- **Control de inventario** — seguimiento de existencias y movimientos.
- **Contabilidad de costos** — costeo asociado al desarrollo y comercialización.
- **Reportes financieros** — balance general, estado de resultados, balanza de comprobación, entre otros.
- **Cálculo de IVA y crédito fiscal** conforme a la legislación salvadoreña.
- **Panel administrativo** construido con Filament.

## 🛠️ Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Laravel 11/12 (PHP) |
| Panel administrativo | Filament v3 |
| Base de datos | PostgreSQL (Supabase) |
| Gestión de dependencias | Composer, npm |

## ✅ Requisitos previos

- PHP 8.2 o superior
- Composer
- Node.js y npm
- Una cuenta/proyecto en [Supabase](https://supabase.com) (o una instancia de PostgreSQL)
- Git
```

## 🗂️ Estructura del proyecto

```text
├── app/
│   ├── Filament/        # Recursos, páginas y widgets del panel
│   ├── Models/          # Modelos Eloquent
│   └── Services/        # Lógica contable (partida doble, cálculos)
├── database/
│   ├── migrations/
│   └── seeders/
├── resources/
├── routes/
└── tests/
```

## 👥 Equipo

| Integrante | Rol |
|-----------|-----|
| Diego | Líder del proyecto |
| David Alexander Rivas Rivas | Desarrollo |
| Josué Nehemias Renderos Hernández | Desarrollo |

## 📄 Licencia
Proyecto elaborado con fines académicos. SunGames S.A de C.V. es una empresa ficticia y todas sus operaciones son simuladas.
