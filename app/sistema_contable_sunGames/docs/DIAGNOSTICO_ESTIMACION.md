# Diagnóstico — Subsistema de Costos / Módulo de Estimación

Fecha: 2026-11-18. Rama: `costos/estimacion` (creada desde `main`).

## Confirmado

- **Stack:** Django 4.2.30 + Python 3.14, PostgreSQL vía `psycopg` (variables
  `DB_*` en `.env`). No hay `docs/PLAN.md` ni `docs/PREGUNTAS.md` de sesiones
  anteriores; el único documento de `docs/` es la especificación de casos de
  uso (DCU Extendido).
- **Ejecución de pruebas:** `python manage.py test` desde
  `app/sistema_contable_Sungames` con el entorno virtual `app/env`.
  Estado base en `main`: **248 pruebas, 52 errores preexistentes**, todos con
  el mismo fallo `AttributeError: 'super' object has no attribute 'dicts'`
  dentro de `django.template.context` al instrumentar el render de plantillas
  con `self.client` (incompatibilidad Django 4.2 / Python 3.14). Las pruebas
  de servicios y repositorios sin renderizado de cliente pasan. Este fallo es
  anterior a este trabajo y no se corrige aquí; las pruebas nuevas del módulo
  evitan depender del renderizado del cliente.
- **Arquitectura:** capas vista → formulario → servicio → repositorio → modelo.
  Cada app de negocio (`usuarios`, `catalogo`, `libro_mayor`, `ventas`,
  `estados_financieros`, `bitacora`) tiene `models.py`, `services.py`,
  `repositories.py`, `exceptions.py`, `composition.py`, `forms.py`, `tests/`
  y, cuando aplica, `admin.py`.
- **Roles:** `usuarios/roles.py` define `Rol` (`TextChoices`) con
  `ADMINISTRADOR` y `CONTADOR_GENERAL`. `AccesoService` (en
  `usuarios/services.py`) define `AREA_INICIAL` y `MODULOS` por rol; es el
  punto que decide qué pantallas ve cada rol. El formulario de alta de
  usuarios (`UsuarioAltaForm`) usa `Rol.choices`, por lo que agregar un valor
  al `TextChoices` habilita al Administrador a registrar el nuevo rol sin más
  cambios.
- **Interfaz:** SPA híbrida en `sic_sunGames/static/sic_sunGames/app.js`.
  Las pantallas `users`, `audit`, `accounts` y `ledger` se renderizan en el
  servidor (templates `sic_sunGames/*.html` que extienden `index.html`,
  con `data-server-rendered="true"` y modales en el bloque `modal`). El resto
  se dibuja en el cliente. La navegación se arma desde `navGroups` filtrada
  por `modulos`; `serverScreens` fuerza navegación completa al servidor.
- **Bitácora:** `bitacora/eventos.py` define `Accion` y `Resultado`
  (`TextChoices`). `BitacoraService.registrar(accion, resultado, ...)` es la
  puerta de registro; `RegistroBitacora` tiene `CheckConstraint` sobre los
  valores válidos, por lo que acciones nuevas requieren ampliar el enum y una
  migración.
- **Libro Mayor:** `libro_mayor/models.py` tiene `PeriodoContable` y
  `Movimiento` (importe firmado, sin partida doble). El módulo de estimación
  no debe tocarlo.
- **Configuración local sucia:** `settings.py` tiene cambios sin commit del
  usuario (DEBUG=False, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS ngrok,
  whitenoise). Se respetan y no se incluyen en los commits del módulo.

## Inferido

- El rol **Contador de Costos** se agrega como nuevo valor de `Rol`
  (p. ej. `CONTADOR_COSTOS`), con área inicial y módulos propios en
  `AccesoService`. El Administrador conserva acceso a todo; el Contador
  General no ve el módulo de estimación.
- La app nueva se llama `estimacion` y sigue la estructura de capas existente.
- Las pantallas del módulo se implementan renderizadas en el servidor,
  siguiendo el patrón de `usuarios.html` (listado + modales), para no tocar el
  renderizador cliente de `app.js` más allá de registrar la pantalla.
- Los parámetros con vigencia (`horas_semana`, `semanas_año`,
  `tasa_cargas_patronales`, `eficiencia`, `umbral_dispersion_delphi`) viven en
  `ParametroVigente` y **no** se fijan en código. Los valores indicados en el
  encargo se cargan como datos semilla vía migración de datos (o comando),
  nunca como constantes de cálculo.
- "Registrar una alerta" cuando falta salario vigente se resuelve con un
  registro en la bitácora (`Resultado.RECHAZADO` + detalle), sin crear una
  tabla de alertas nueva. Ver `docs/PREGUNTAS.md`.
