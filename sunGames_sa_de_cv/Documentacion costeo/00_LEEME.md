# Documentación de costeo — SunGames, S.A. de C.V.

Documentación operativa con la que SunGames costea el desarrollo de sus videojuegos. El costo se
estima antes de abrir la orden y se acumula durante la producción. Cada método tiene su carpeta, su
manual y su expediente de soportes.

Los documentos llevan el nombre, el membrete y el sello de la empresa. Son de uso interno y
confidencial.

## Estructura

| Ruta | Contenido | Cuándo se usa |
|------|-----------|---------------|
| `00_Anexo_A_Investigacion_y_seleccion_de_metodos_de_costeo.docx` | Investigación técnica que sustenta la elección del método y de la técnica de estimación (SG-CTL-003). | Para entender por qué se costea así. Es común a las dos carpetas. |
| `Costeo por juicio de experto/` | Manual SG-CTL-002, libro de estimación en Excel y soportes SJE-01 a SJE-10. | Antes de abrir una orden: estima horas, tarifas, CIF y fija la línea base. |
| `Costeo por ordenes de trabajo/` | Manual SG-CTL-001, documento de órdenes de trabajo v2, hoja de costos en Excel y soportes SOP-01 a SOP-10. | Durante la producción: registra horas, aplica CIF, calcula variaciones y amortiza el título. |

Cada carpeta tiene su propio `00_LEEME.md` con el índice detallado, el orden de lectura y las cifras
de referencia.

## Cómo se relacionan los dos métodos

1. **Juicio de experto** estima la línea base del proyecto: horas por programador, costo de mano de
   obra, CIF presupuestados y tasa predeterminada. Termina con el acta SJE-10.
2. La línea base aprobada abre la **orden de trabajo**, que acumula los costos reales mes a mes.
3. **Órdenes de trabajo** compara lo real contra la línea base, calcula variaciones, traslada el
   costo al activo y amortiza el título terminado.
4. Si el alcance cambia, el panel de expertos emite una nueva versión de la línea base y la orden se
   ajusta. La versión anterior no se borra.

## Guía de lectura

1. **Anexo A.** Explica los métodos de costeo, los criterios de selección y la técnica de estimación.
2. **Costeo por juicio de experto.** Muestra cómo se estimó la línea base del primer título.
3. **Costeo por ordenes de trabajo.** Muestra cómo se ejecuta y se registra esa línea base.
4. Los Excel permiten recalcular cada cifra; los soportes prueban cada valor.

## Cifras de referencia — orden SG-TIT-01 (Aurora Salvaje)

| Concepto | Importe |
|----------|---------|
| Presupuesto total de la orden | USD 30,300.00 |
| Mano de obra presupuestada (4,000 h) | USD 25,500.00 |
| CIF presupuestados | USD 4,800.00 |
| Tasa predeterminada | USD 1.20 por hora |
| Horas reales de marzo de 2026 | 330.00 h |
| Mano de obra real de marzo | USD 2,160.00 |
| CIF aplicado | USD 396.00 |
| CIF real | USD 410.00 |
| Subaplicación | USD 14.00 |
| Costo trasladado a 1106 | USD 2,556.00 |
| Variación total de MOD al cierre (programador B) | USD 1,000.00 (horas 600.00 + tarifa 400.00) |

## Cuentas usadas

Se adoptó el **Anexo 3 del Manual de aplicación del catálogo de cuentas**:

- `1106` Videojuegos en desarrollo
- `1107` Videojuegos terminados
- `1108` Amortización acumulada de videojuegos
- `1109` IVA crédito fiscal
- `1111` Anticipos a proveedores
- `1204` Licencias de software · `1205` Amortización acumulada de licencias
- `4101` Mano de obra directa · `4103` Costos indirectos de desarrollo · `4104` Costo de ventas
- `4502` Gastos por servicios profesionales · `4503` Impuesto sobre la renta

## Diferencias documentales reportadas

| Punto | Referencia en conflicto | Decisión |
|-------|------------------------|----------|
| Cuentas de videojuegos | Política 4 usa 1204/1205/1206; Anexo 3 usa 1106/1107/1108 | Se usa el Anexo 3. TODO para corregir la Política 4. |
| IVA crédito fiscal | Política 8 usa 1106; Anexo 3 usa 1109 | Se usa 1109. TODO para corregir la Política 8. |
| Impuesto sobre la renta | El cierre usa 4502; Anexo 3 usa 4503 | Se usa 4503. TODO para corregir el cierre. |
| Anticipos | RF-077 usa 1108; Anexo 3 usa 1111 | Se usa 1111. |
| Tasa de CIF | RF-057 por orden; RF-092 por período | Se usa la tasa por período. |
| Rol responsable | DCU y SRS: Contador de Costos; AGENTS.md lo difiere | Opera el Contador General como «responsable de costos». |

## Notas

- Los `.docx` se generaron con `python-docx`; los `.xlsx`, con `openpyxl`. Las propiedades de los
  26 archivos quedaron normalizadas: autor `SunGames, S.A. de C.V.`, último cambio
  `Departamento de Contabilidad` y categoría «Documento interno — confidencial».
- Las fórmulas de los libros se verificaron con recálculo real en Excel.
- Fechas en formato dd/mm/aaaa e importes en USD con dos decimales, conforme a `AGENTS.md`.
- El documento `02_Ordenes_de_trabajo_v2.docx` (código `SG-CTL-004`) usa la misma portada
  corporativa que el resto de la serie. La versión 1.0 se presentó en el curso SIC115 y la versión
  2.0 se emitió ya como documento interno de SunGames; su contenido describe la operación real de la
  empresa.
- Serie de control documental: `SG-CTL-001` manual de órdenes de trabajo, `SG-CTL-002` manual de
  juicio de expertos, `SG-CTL-003` Anexo A y `SG-CTL-004` documento de órdenes de trabajo v2.
