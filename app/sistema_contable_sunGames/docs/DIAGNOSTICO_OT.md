# Fase O0 — Diagnóstico: Órdenes de Trabajo (costeo real)

Rama: `costos/ordenes-trabajo` (creada desde `main`).
Fecha: 2026-11-18.
Alcance: solo lectura. No se modificó código de contabilidad general ni de
estimación (esta última no existe en `main`; vive en `costos/estimacion`).

## Confirmado en el código

### Stack y arquitectura

- Python 3.14 + Django 4.2.30, PostgreSQL vía variables de entorno
  (`sistema_contable_sunGames/settings.py`); existe `db.sqlite3` local
  pero la configuración apunta a PostgreSQL.
- Templates de Django renderizados en servidor + JS vanilla
  (`sic_sunGames/static/sic_sunGames/app.js`, `styles.css`). Sin
  framework de frontend.
- Arquitectura en capas: vista → formulario → servicio → repositorio →
  modelo, con composición por `composition.py` por app y excepciones de
  dominio (reglas en `AGENTS.md`).
- Pruebas: `python manage.py test` con el venv `app/env`
  (`app/env/Scripts/python.exe`). En la rama de estimación la suite
  completa mostraba 52 errores preexistentes por incompatibilidad
  Django 4.2 / Python 3.14 al instrumentar plantillas en tests de
  cliente; no son del módulo nuevo.
- `docs/` en `main` solo contiene la especificación DCU; no hay
  `PLAN.md`, `PREGUNTAS.md` ni `AVANCE.md` previos en esta rama.

### Mecanismo de registro en el mayor

- **No existe entidad "Asiento" con partida doble.** El mayor es
  `Transaccion` (agrupador) + `Movimiento` (línea con importe firmado:
  positivo = Debe, negativo = Haber), en
  `libro_mayor/models.py:94-188`.
- `Movimiento.save()` rechaza fechas en período cerrado
  (`libro_mayor/models.py:168-188`); el queryset bloquea `update` y
  `delete` masivos (`libro_mayor/models.py:112-124`).
- `LibroMayorService.registrar` (`libro_mayor/services.py:191-209`)
  registra movimientos en **una sola cuenta por llamada** y **no exige
  cuadre** (confirmado también en `AGENTS.md`: "El sistema no exige que
  una transacción cuadre").
- **Precedente multi-cuenta**: `ventas/services.py:222-261`
  (`contabilizar`) crea una `Transaccion` y varios `Movimiento` en
  cuentas distintas usando `TransaccionRepository.crear_transaccion` /
  `crear_movimiento` (`libro_mayor/repositories.py:46-55`), valida
  cuenta activa y sin subcuentas, período abierto, todo dentro de
  `transaction.atomic`, con idempotencia propia
  (`venta.transaccion_id`) y registro en bitácora. **Este es el patrón
  que el módulo de costos puede reutilizar sin modificar el mayor.**
- El cuadre debe=haber no lo valida nadie: el módulo de costos debe
  verificarlo antes de enviar (requisito del encargo).
- `Movimiento` **no tiene campo auxiliar/orden de trabajo**: solo
  cuenta, fecha, concepto (200), referencia (40), tipo y
  importe (`libro_mayor/models.py:126-154`). La trazabilidad por orden
  deberá ir en concepto/referencia y en tablas propias del módulo.

### Períodos y cierres

- `PeriodoContable` (`libro_mayor/models.py:39-91`) con estados
  `ABIERTO` / `CIERRE_PROVISIONAL`; helper `cerrado_en(fecha)`.
- `TransaccionRepository.periodo_de(fecha)`
  (`libro_mayor/repositories.py:16-24`) devuelve el período que contiene
  la fecha (prefiere el cerrado) y lanza `FechaInvalidaError` si ningún
  período cubre la fecha → un cargo sin período contable que lo cubra
  no se puede registrar.
- El "cierre" de `estados_financieros`
  (`estados_financieros/services.py:293-392`) emite snapshots de estados
  financieros y marca el período; **no genera asientos de cierre** ni
  toca el mayor. La reapertura exige administrador + contraseña
  (`services.py:315-339`).
- El "cierre provisional" del encargo OT (traslado 4101-4103 →
  intangible, reversible) es propio del módulo de costos; no existe hoy.

### Catálogo de cuentas (semilla `catalogo/migrations/0004_catalogo_inicial.py`)

Presentes y relevantes:

- `4101` Mano de obra directa de desarrollo, `4102` Servicios directos
  de desarrollo, `4103` Costos indirectos de desarrollo, `4104` Costo de
  ventas (subtipo 4-1 "Costos de desarrollo", naturaleza deudora).
- `1106` Videojuegos en desarrollo, `1107` Videojuegos terminados,
  `1108` Amortización acumulada de videojuegos.
- `2105` Cargas patronales por pagar, `2106` Sueldos y prestaciones por
  pagar.
- `4201` Sueldos y salarios administrativos, `4202` Prestaciones y
  cargas patronales, `4207` Depreciación de mobiliario y equipo.
- `1201` Mobiliario y equipo de oficina, `1202` Equipo de cómputo,
  `1203` Depreciación acumulada.
- Rubros 6 y 7 (cuentas de orden) existen en el catálogo.

**No existe** una cuenta llamada "intangible en desarrollo" ni
"intangible en uso"; las candidatas naturales son `1106`/`1107`
(activo, no intangible estricto). Ver `docs/PREGUNTAS.md`.

### Roles y acceso

- En `main`, `usuarios/roles.py` solo define `ADMINISTRADOR` y
  `CONTADOR_GENERAL`. `CONTADOR_COSTOS` existe únicamente en la rama
  `costos/estimacion` (no fusionada).
- `AccesoService` (`usuarios/services.py:178-206`) define área inicial y
  módulos por rol; un módulo nuevo requiere registrarse ahí y en
  `SCREEN_URL_NAMES` (`sic_sunGames/views/pages.py:14-22`).

### Bitácora

- `bitacora/eventos.py`: `Accion` y `Resultado` como `TextChoices`;
  agregar acciones exige migración (precedente en la rama estimación).

### Interfaz

- Layout compartido: `sic_sunGames/templates/sic_sunGames/index.html` +
  `base.html`, contexto común `contexto_panel`
  (`sic_sunGames/views/pages.py:34-73`) con `modulos`, `screen_urls` y
  estado del período.
- Tokens de diseño en `styles.css` (`:root`: navy/gold/ink, sombras,
  tipografía DM Sans/Manrope). Modales server-rendered con
  `modal-backdrop`/`modal` (patrón de `usuarios.html` en la rama
  estimación; en `main` los modales de cierre son parciales + JS en
  `app.js` con `#modalRoot`).
- Paginación: `sic_sunGames/templates/sic_sunGames/paginacion.html` +
  `django.core.paginator` en vistas.

## Inferido (no confirmado en código)

- "Cuenta de origen del gasto" para mano de obra/prestaciones: el
  catálogo tiene pasivos por pagar (2105, 2106) y gastos administrativos
  (4201, 4202), pero ningún asiento previo muestra cuál se usa como
  contrapartida de los costos de desarrollo. → `PREGUNTAS.md`.
- La "tasa por hora de proceso" necesita el costo del proceso en el
  período; no existe aún quién lo calcule (¿captura manual o integración
  con gasto real?). → `PREGUNTAS.md`.
- El auxiliar por orden de trabajo no existe en `Movimiento`; se asume
  trazabilidad por concepto/referencia + tabla propia hasta que se
  apruebe otra cosa. → `PREGUNTAS.md`.
- Salario de referencia para mano de obra: la tabla equivalente vive en
  la app `estimacion` (prohibido depender de ella); habrá que crear una
  tabla propia en el módulo de costos. → `PREGUNTAS.md`.
- Responsive: `styles.css` tiene breakpoints (no auditados en detalle);
  la conversión de tablas a tarjetas en móvil probablemente requiera CSS
  nuevo dentro del mismo sistema de tokens.
