# Clases principales y relaciones del sistema

Este documento resume las entidades persistidas definidas en los `models.py` de Django y sus relaciones declaradas mediante `ForeignKey`, `OneToOneField` y `ManyToManyField`. Sirve como base para dibujar o actualizar el diagrama de clases del sistema.

Los diagramas muestran relaciones del modelo de datos; no agregan dependencias que solo existan en servicios o vistas. Los extremos indican multiplicidad. Las flechas van desde el modelo que declara la referencia hacia el modelo referenciado.

## 1. Identidad, catálogo, mayor, ventas y estados financieros

```mermaid
classDiagram
direction LR

class Usuario {
  username
  nombre_completo
  rol : choices
  activo
}
class RegistroBitacora {
  fecha_hora
  accion
  resultado
  referencia
}
class Rubro {
  codigo
  nombre
}
class Subtipo {
  codigo
  nombre
}
class Naturaleza {
  codigo
  nombre
}
class Cuenta {
  codigo
  denominacion
  activa
}
class AprobacionCuenta {
  tipo
  acuerdo_numero
  acuerdo_fecha
}
class HistorialCuenta {
  campo
  valor_anterior
  valor_nuevo
}
class PeriodoContable {
  nombre
  fecha_inicio
  fecha_fin
  estado
}
class Transaccion {
  fecha_registro
}
class Movimiento {
  fecha
  concepto
  importe : firmado
}
class EstadoFinancieroEmitido {
  tipo
  datos : JSON
  fecha_emision
}
class Venta {
  identificador
  tipo_producto
  cantidad
  estado
}
class ConexionSteam {
  ultimo_contacto
  ultimo_error
}

RegistroBitacora "0..*" --> "0..1" Usuario : actor
RegistroBitacora "0..*" --> "0..1" Usuario : afectado
Subtipo "0..*" --> "1" Rubro : rubro
Cuenta "0..*" --> "1" Rubro : rubro
Cuenta "0..*" --> "1" Subtipo : subtipo
Cuenta "0..*" --> "1" Naturaleza : naturaleza
AprobacionCuenta "0..*" --> "1" Cuenta : cuenta
AprobacionCuenta "0..*" --> "1" Usuario : usuario
HistorialCuenta "0..*" --> "1" AprobacionCuenta : aprobacion
Transaccion "0..*" --> "1" Usuario : usuario
Movimiento "0..*" --> "1" Transaccion : transaccion
Movimiento "0..*" --> "1" Cuenta : cuenta
EstadoFinancieroEmitido "0..*" --> "1" PeriodoContable : periodo
EstadoFinancieroEmitido "0..*" --> "1" Usuario : usuario
Venta "0..1" --> "0..1" Transaccion : transaccion opcional
```

## 2. Costos y vínculo con la estimación

```mermaid
classDiagram
direction LR

class JuegoCostos["Juego (costos.Juego)"] {
  nombre
  fecha_creacion
}
class OrdenTrabajo {
  estado
  fecha_inicio
  licencias_estimadas
  eliminado_en
}
class VersionPresupuesto["VersionPresupuesto (estimacion)"] {
  numero
  estado
  fecha
  eliminado_en
}
class JuegoEstimacion["Juego (estimacion.Juego)"] {
  nombre
  fecha_creacion
}
class Proceso {
  nombre
  costo_hora
  activo
}
class ConfiguracionCuentaCosto {
  elemento : unico
}
class FuenteIndirecta {
  nombre
  tipo
  exclusiva_desarrollo
  activa
}
class CuentaIndirectaExcluida {
  motivo
  creada_en
}
class RegistroCosto {
  elemento
  fecha
  horas
  importe
  estado
}
class AsientoCosto {
  tipo
  clave_idempotencia
}
class Cuenta {
  codigo
  denominacion
}
class Usuario {
  username
  nombre_completo
}
class PeriodoContable {
  nombre
  estado
}
class Transaccion {
  fecha_registro
}

OrdenTrabajo "0..*" --> "1" JuegoCostos : maximo una orden activa por juego
OrdenTrabajo "0..1" --> "0..1" VersionPresupuesto : estimacion_ref
VersionPresupuesto "0..*" --> "1" JuegoEstimacion : juego
OrdenTrabajo "0..*" --> "0..1" Usuario : creado_por opcional
OrdenTrabajo "0..*" --> "0..1" Usuario : eliminado_por opcional
ConfiguracionCuentaCosto "0..*" --> "1" Cuenta : cuenta_costo
ConfiguracionCuentaCosto "0..*" --> "1" Cuenta : contrapartida_defecto
ConfiguracionCuentaCosto "0..*" --> "0..*" Cuenta : contrapartidas permitidas
FuenteIndirecta "0..1" --> "1" Cuenta : cuenta_origen uno-a-uno
FuenteIndirecta "0..*" --> "0..1" Proceso : proceso opcional
CuentaIndirectaExcluida "0..1" --> "1" Cuenta : cuenta uno-a-uno
CuentaIndirectaExcluida "0..*" --> "1" Usuario : creada_por
RegistroCosto "0..*" --> "1" OrdenTrabajo : orden
RegistroCosto "0..*" --> "0..1" Proceso : proceso opcional
RegistroCosto "0..*" --> "1" Cuenta : cuenta_costo
RegistroCosto "0..*" --> "1" Cuenta : contrapartida
RegistroCosto "0..*" --> "0..1" FuenteIndirecta : fuente_indirecta
RegistroCosto "0..*" --> "0..1" PeriodoContable : periodo_indirecto
RegistroCosto "0..*" --> "1" Usuario : usuario
RegistroCosto "0..*" --> "0..1" Usuario : anulado_por opcional
VersionPresupuesto "0..*" --> "0..1" Usuario : eliminado_por opcional
AsientoCosto "0..1" --> "1" Transaccion : transaccion uno-a-uno
AsientoCosto "0..*" --> "1" OrdenTrabajo : orden
AsientoCosto "0..2" --> "1" RegistroCosto : registro
```

## 3. Estimación de presupuesto

```mermaid
classDiagram
direction LR

class JuegoEstimacion["Juego (estimacion.Juego)"] {
  nombre
}
class Rol {
  nombre
  nivel
}
class SalarioReferencia {
  salario_bruto
  vigente_desde
  vigente_hasta
}
class ParametroVigente {
  clave
  valor
  vigente_desde
  vigente_hasta
  verificado
}
class FaseEstimacion {
  nombre
  orden
  clasificacion
}
class Experto {
  nombre
}
class EstimacionExperto {
  ronda
  optimista
  moda
  pesimista
  eliminado_en
}
class RondaDelphi {
  numero
  cerrada
  resultado : JSON
}
class VersionPresupuesto {
  numero
  estado
  snapshot_parametros : JSON
}
class LineaPresupuesto {
  horas_E
  sigma
  tarifa
  costo_mano_obra
}
class CostoFabricacion {
  tipo
  concepto
  monto
}
class CostoDirectoEstimado {
  concepto
  monto
}
class CostoIndirectoEstimado {
  departamento
  monto
}
class Usuario {
  username
  nombre_completo
}

SalarioReferencia "0..*" --> "1" Rol : rol
FaseEstimacion "0..*" --> "1" JuegoEstimacion : juego
EstimacionExperto "0..*" --> "1" JuegoEstimacion : juego
EstimacionExperto "0..*" --> "1" FaseEstimacion : fase
EstimacionExperto "0..*" --> "1" Rol : rol
EstimacionExperto "0..*" --> "1" Experto : experto
EstimacionExperto "0..*" --> "0..1" Usuario : eliminado_por opcional
RondaDelphi "0..*" --> "1" JuegoEstimacion : juego
RondaDelphi "0..*" --> "0..1" Usuario : aprobada_por opcional
VersionPresupuesto "0..*" --> "1" JuegoEstimacion : juego
VersionPresupuesto "0..*" --> "1" Usuario : autor
LineaPresupuesto "0..*" --> "1" VersionPresupuesto : version
LineaPresupuesto "0..*" --> "1" FaseEstimacion : fase
LineaPresupuesto "0..*" --> "1" Rol : rol
CostoFabricacion "0..*" --> "1" JuegoEstimacion : juego
CostoDirectoEstimado "0..*" --> "1" VersionPresupuesto : version
CostoIndirectoEstimado "0..*" --> "1" VersionPresupuesto : version
```

## Relaciones importantes para interpretar

- **Orden y estimación:** `OrdenTrabajo.estimacion_ref` es una clave foránea nullable a `estimacion.VersionPresupuesto`. La restricción única para órdenes activas hace que cada versión se relacione con cero o una orden activa; una orden puede no tener versión o tener una. Archivar una orden libera esa versión para otra orden. La relación no está limitada a versiones con un estado específico por la definición del campo.
- **Dos modelos `Juego`:** `costos.Juego` y `estimacion.Juego` son clases y tablas diferentes. La orden apunta a `costos.Juego`; la versión del presupuesto apunta a `estimacion.Juego`. El modelo no declara una clave foránea entre ambos juegos ni comprueba que sus nombres coincidan. La conexión entre costeo y estimación ocurre a través de `OrdenTrabajo.estimacion_ref`.
- **Usuario y rol:** `usuarios.Usuario.rol` es un campo de texto con opciones, no una relación a otra tabla. `estimacion.Rol` sí es un modelo persistido y representa puestos/niveles usados para estimar.
- **Configuración de cuentas:** `ConfiguracionCuentaCosto` contiene dos claves foráneas a `catalogo.Cuenta` y una relación muchos-a-muchos adicional para las contrapartidas permitidas.
- **Costos indirectos automáticos:** `RegistroCosto.fuente_indirecta` y `periodo_indirecto` son opcionales individualmente en la base, pero la restricción del modelo exige que ambos estén presentes juntos y que el elemento sea indirecto.
- **Periodo del movimiento:** `libro_mayor.Movimiento` no tiene clave foránea a `PeriodoContable`; el período se determina por la fecha del movimiento. En cambio, los estados financieros emitidos sí guardan una relación directa con el período.
- **Relaciones opcionales:** en el diagrama, `0..1` corresponde a claves foráneas `null=True` o a un lado único opcional. Las relaciones uno-a-uno inversas pueden no tener objeto relacionado todavía.
- **Baja lógica:** `OrdenTrabajo`, `EstimacionExperto` y `VersionPresupuesto` guardan `eliminado_en` y `eliminado_por`; archivar no borra el registro ni sus vínculos. El par de campos debe estar completo o vacío. Se puede conservar más de una orden histórica por juego, con un máximo de una activa.
- **Versiones inmutables:** las versiones aprobadas, vigentes o rechazadas no permiten editar sus datos de presupuesto. La baja/restauración solo cambia los metadatos de archivo; las correcciones de presupuesto se representan con una versión nueva.
- **Choices no son clases/tablas:** estados, tipos, elementos, acciones y roles de usuario definidos con `TextChoices` o listas de opciones se guardan como campos del modelo; no se muestran como entidades relacionadas.

## Modelos fuente

- [Usuarios](../usuarios/models.py)
- [Bitácora](../bitacora/models.py)
- [Catálogo de cuentas](../catalogo/models.py)
- [Libro Mayor](../libro_mayor/models.py)
- [Estados financieros](../estados_financieros/models.py)
- [Ventas](../ventas/models.py)
- [Costos](../costos/models.py)
- [Estimación](../estimacion/models.py)
