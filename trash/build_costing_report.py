from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sunGames_sa_de_cv" / "Diseno_Contable_y_Costos" / "Investigacion_y_Aplicacion_Metodos_Costeo_SunGames_SA_de_CV.docx"

NAVY = "23395B"
BLUE = "DCE6F1"
PALE = "F3F6FA"
GRAY = "D9D9D9"
BLACK = "000000"

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.72)
sec.bottom_margin = Inches(0.72)
sec.left_margin = Inches(0.78)
sec.right_margin = Inches(0.78)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Arial"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
normal.font.size = Pt(10)
normal.font.color.rgb = RGBColor.from_string(BLACK)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12

for stylename, size in (("Title", 24), ("Heading 1", 15), ("Heading 2", 12), ("Heading 3", 10.5)):
    style = styles[stylename]
    style.font.name = "Arial"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    style.font.size = Pt(size)
    style.font.bold = stylename != "Title"
    style.font.color.rgb = RGBColor.from_string(BLACK)
    style.paragraph_format.keep_with_next = True
    style.paragraph_format.space_before = Pt(12 if stylename != "Title" else 0)
    style.paragraph_format.space_after = Pt(5)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_borders(cell, color=GRAY, size="6"):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_cell_text(cell, text, bold=False, color=BLACK, size=8.8):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(str(text))
    run.bold = bold
    run.font.name = "Arial"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    set_cell_borders(cell)


def add_table(headers, rows, widths=None, font_size=8.8):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    table.style = "Table Grid"
    if widths:
        for i, width in enumerate(widths):
            table.columns[i].width = Inches(width)
    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for i, label in enumerate(headers):
        set_cell_text(header.cells[i], label, bold=True, color="FFFFFF", size=font_size)
        set_cell_shading(header.cells[i], NAVY)
        if widths:
            header.cells[i].width = Inches(widths[i])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        prevent_row_split(table.rows[-1])
        for cidx, value in enumerate(row):
            set_cell_text(cells[cidx], value, size=font_size)
            if widths:
                cells[cidx].width = Inches(widths[cidx])
            if ridx % 2 == 1:
                set_cell_shading(cells[cidx], PALE)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_bullet(text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.space_after = Pt(3)
    p.add_run(text)
    return p


def add_number(text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(4)
    p.add_run(text)
    return p


def add_hyperlink(paragraph, text, url):
    rel_id = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F4E79")
    props.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    props.append(underline)
    run.append(props)
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_ref(number, citation, url):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.paragraph_format.space_after = Pt(4)
    p.add_run(f"[{number}] {citation} ")
    add_hyperlink(p, "Fuente", url)


def add_page_field(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


# Cover
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(72)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("SUN GAMES S.A. DE C.V.")
r.bold = True
r.font.name = "Arial"
r.font.size = Pt(13)
r.font.color.rgb = RGBColor.from_string(NAVY)

p = doc.add_paragraph(style="Title")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(28)
p.paragraph_format.space_after = Pt(14)
p.add_run("Investigación y aplicación de métodos de costeo")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(34)
r = p.add_run("Estimación de software por juicio de expertos y costeo por órdenes de trabajo")
r.font.name = "Arial"
r.font.size = Pt(14)
r.font.color.rgb = RGBColor.from_string(BLACK)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(28)
p.add_run("Informe técnico para definir necesidades, políticas y requerimientos del módulo de contabilidad de costos")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(68)
p.add_run("Preparado para la dirección y el área contable de SunGames S.A. de C.V.")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(8)
p.add_run("San Salvador, El Salvador | 1 de noviembre de 2026")

doc.add_page_break()

doc.add_heading("Resumen ejecutivo", level=1)
doc.add_paragraph(
    "Se recomienda integrar dos técnicas que resuelven problemas distintos. SunGames puede usar el juicio de expertos para preparar y aprobar el presupuesto inicial de cada videojuego o contrato de software, y el costeo por órdenes de trabajo para registrar los costos reales y compararlos con ese presupuesto. El objeto principal será cada título propio; los servicios de desarrollo para clientes se manejarán en órdenes independientes. La estimación crea una línea base; no reemplaza facturas, planillas ni registros de horas. [6][7][8]"
)
doc.add_paragraph(
    "Para el producto principal, los documentos de SunGames identifican un título desarrollado por cuenta propia y comercializado mediante licencias en Steam. El informe adopta como unidad de costeo el videojuego completo y sus fases, con el código de prueba SG-TIT-01; SG-CON-01 queda como objeto secundario para un desarrollo por encargo. [D3]"
)
doc.add_paragraph(
    "Antes de automatizar traslados a activos o amortizaciones, SunGames debe aprobar una política contable sobre la naturaleza del videojuego licenciado. La NIIF para las PYMES incluye inventarios en proceso de producción o mantenidos para la venta, y requiere identificación específica de costos para bienes o servicios segregados por proyecto. A la vez, la Sección 18 exige llevar a gasto los desembolsos internos de investigación y desarrollo cuando se trata de un intangible generado internamente fuera del alcance de inventarios. La clasificación depende de los derechos, los términos de la licencia y el modelo de distribución. [1][2][3]"
)
doc.add_paragraph(
    "Los requerimientos actuales ya prevén órdenes, horas, tarifas, costos indirectos y reportes, pero dejan pendiente el método para estimar horas y contienen diferencias entre cuentas, tratamiento de servicios externos y capitalización. La propuesta de este informe conserva el auxiliar por orden y bloquea las partidas automáticas hasta aprobar el marco contable y armonizar el catálogo. [D1][D2][D4]"
)

doc.add_heading("1. Propósito, alcance y perfil de SunGames", level=1)
doc.add_paragraph(
    "El propósito es definir cómo estimar y acumular el costo de los proyectos de software de SunGames, qué documentos y controles debe conservar el módulo, y cómo conectar el costeo con la contabilidad financiera y tributaria salvadoreña. El análisis se apoya en los requerimientos funcionales y no funcionales, la especificación generada, el modelo de negocio y los documentos internos sobre diseño contable y costos."
)
doc.add_paragraph(
    "SunGames es una desarrolladora salvadoreña de videojuegos. El modelo documentado contempla títulos propios comercializados mediante licencias digitales por Steam, además de mantenimiento y soporte técnico; el diseño de costos reserva también órdenes para desarrollo por encargo. La empresa opera en USD y tiene equipos de programación, arte/diseño, control de calidad, administración y contabilidad. [D1][D3][D5]"
)
doc.add_paragraph(
    "El informe cubre estimación de presupuesto, costeo gerencial por proyecto, evidencia y trazabilidad, tratamiento de costos de títulos propios, distinción frente a contratos de clientes y requerimientos que faltan. No fija tasas tributarias, cargas laborales, retenciones ni tiempos de respuesta no comprobados; estos parámetros deben ser configurables y tener una fuente y fecha de vigencia."
)

doc.add_heading("2. Cómo se relacionan los dos métodos", level=1)
add_table(
    ["Método", "Pregunta que responde", "Uso propuesto en SunGames"],
    [
        ["Juicio de expertos", "¿Cuántas horas y recursos harán falta para completar el alcance y cuánto costarán?", "Presupuesto inicial, pronóstico a término, escenarios y reservas explicadas."],
        ["Órdenes de trabajo", "¿Qué costos reales consumió cada título, fase o contrato y qué parte de indirectos le corresponde?", "Auxiliar por proyecto con horas aprobadas, comprobantes, tarifa aplicable e indirectos asignados."],
        ["Comparación y control", "¿Dónde se apartó el resultado del presupuesto y por qué?", "Variaciones de horas, tarifa y costos indirectos; revisión del alcance y actualización del pronóstico."],
    ],
    widths=[1.35, 2.75, 3.05],
)
doc.add_paragraph(
    "El juicio de expertos es una técnica de estimación de proyectos, no un método de acumulación contable. El costeo por órdenes es una estructura para reunir costos identificables con trabajos particulares y aplicar costos comunes mediante una base racional. En SunGames se complementan: expertos establecen el presupuesto y la orden conserva la evidencia de lo que efectivamente se gastó. [6][7][9]"
)

doc.add_heading("3. Estimación de costos de software por juicio de expertos", level=1)
doc.add_heading("3.1 Definición y límites", level=2)
doc.add_paragraph(
    "El juicio de expertos estima esfuerzo, duración y costo con la experiencia de personas que conocen el dominio técnico y el trabajo. Es especialmente útil al iniciar un título, cuando los datos históricos propios todavía son pocos. NASA describe el juicio experto como una de varias técnicas que suelen combinarse con analogías, modelos o datos históricos. La experiencia reciente en el mismo dominio mejora su utilidad, pero el resultado conserva incertidumbre y puede reflejar sesgos. [6][7][8]"
)
doc.add_paragraph(
    "Por ello, cada estimación de SunGames debe identificar alcance, supuestos, fuentes, responsables, rango de incertidumbre y fecha. La estimación aprobada no debe contabilizar costos ni reemplazar el registro posterior de tiempo, planilla, factura o entregable. Una estimación revisada genera una versión nueva; no borra el presupuesto original."
)

doc.add_heading("3.2 Procedimiento propuesto", level=2)
for text in [
    "Definir el producto y la base técnica: género y plataformas objetivo, funcionalidades, calidad esperada, idiomas, fecha de lanzamiento, entregables, restricciones de motor/licencias y exclusiones. Congelar la versión inicial del alcance.",
    "Descomponer el trabajo en fases y paquetes estimables: concepto y preproducción; diseño; programación; arte, animación y audio; integración; pruebas y control de calidad; publicación. Cada paquete debe tener responsable y criterio de aceptación.",
    "Convocar un grupo pequeño con conocimiento directo: líder técnico, programación, arte/diseño, control de calidad y responsable del proyecto; el contador de costos valida tarifas, conceptos y consistencia, y una persona facilita la estimación sin imponer un resultado.",
    "Solicitar estimaciones individuales por rol y paquete antes de discutirlas. Registrar horas optimistas, más probables y pesimistas, explicación, nivel de confianza y riesgos. No convertir horas a importes hasta aplicar la tarifa salarial o cotización con vigencia documentada.",
    "Realizar una ronda de revisión tipo Delphi o consenso estructurado: comparar diferencias, pedir evidencia, revisar dependencias y riesgos, y repetir la estimación si el alcance cambia. Registrar acuerdos y desacuerdos; evitar que la opinión más jerárquica se convierta automáticamente en consenso.",
    "Convertir esfuerzo a dinero con tarifas internas cargadas aprobadas y cotizaciones de terceros. Para el rango de esfuerzo se puede aplicar como convención de SunGames la fórmula ponderada (optimista + 4 x más probable + pesimista) / 6; esta fórmula debe etiquetarse como regla interna, no como exigencia legal o NIIF.",
    "Consolidar costos directos e indirectos por fase. Separar contingencia identificada de la estimación base y mostrar los riesgos que la justifican. Contrastar el resultado con proyectos comparables disponibles y explicar cualquier ajuste.",
    "Emitir una línea base de presupuesto y horas por orden, fase, rol, tarifa, período y fuente. Obtener revisión del responsable de proyecto y aprobación de la Junta Directiva o instancia autorizada. Rebaselinar solo con cambio de alcance o decisión aprobada.",
    "Comparar cada cierre mensual los costos reales y las horas aprobadas con la línea base. Mantener el pronóstico a término y las variaciones junto al presupuesto original; usar los datos cerrados para mejorar estimaciones de juegos posteriores. [7][9]",
]:
    add_number(text)

doc.add_heading("3.3 Datos que debe guardar la estimación", level=2)
add_table(
    ["Dato", "Regla para SunGames"],
    [
        ["Identificación y versión", "Código de proyecto y orden, título, fecha, versión del presupuesto, responsable y estado de aprobación."],
        ["Alcance y descomposición", "Fase, paquete, entregable, rol, plataforma, supuestos, exclusiones y criterios de aceptación."],
        ["Horas y tarifas", "Horas baja/base/alta por rol; tarifa por hora y vigencia; fuente de tarifa; cotización/contrato de terceros."],
        ["Base del juicio", "Nombre y función de estimadores, experiencia relevante, fecha de cada ronda, observaciones y método de consenso."],
        ["Riesgo y confianza", "Rango, nivel de confianza, riesgos, mitigaciones y contingencia separada por causa."],
        ["Control de cambios", "Presupuesto original, pronóstico vigente, diferencias, justificación y aprobador de cada cambio."],
    ],
    widths=[1.55, 5.6],
)

doc.add_heading("4. Costeo por órdenes de trabajo", level=1)
doc.add_heading("4.1 Adecuación a la producción de videojuegos", level=2)
doc.add_paragraph(
    "Una orden de trabajo acumula costos por trabajo individual cuando los productos o proyectos son distintos y sus costos pueden trazarse de forma útil. La hoja de costos reúne costos directos y costos indirectos aplicados; la mano de obra se registra por horas del empleado y los costos indirectos se distribuyen mediante una tasa predeterminada ligada a una base de actividad. [10][11]"
)
doc.add_paragraph(
    "Para SunGames el objeto principal es el título completo, subdividido por fases y centros de costo. El juego no debe confundirse con cada descarga ni con cada licencia emitida. La unidad por orden permite conocer el costo de producir el título, seguir su avance, comparar el presupuesto y analizar su rentabilidad. Los ingresos por licencia, descuentos, reembolsos y comisión de Steam se concilian por separado con los reportes de plataforma."
)

doc.add_heading("4.2 Objetos y códigos de trabajo", level=2)
add_table(
    ["Tipo", "Código inicial", "Unidad y separación"],
    [
        ["Título propio", "SG-TIT-01", "Un videojuego original por orden; auxiliares por fase, rol, centro de costo y período."],
        ["Desarrollo por encargo", "SG-CON-01", "Una orden por contrato/cliente, con alcance, entregables e hitos contractuales."],
        ["Soporte y mantenimiento", "Código por juego y período", "Orden separada para actualizaciones, parches y soporte; no mezclar con producción original."],
        ["Costos compartidos", "Centro/pool indirecto", "Acumular primero por pool y período; asignar a proyectos elegibles mediante base aprobada."],
    ],
    widths=[1.55, 1.5, 4.1],
)

doc.add_heading("4.3 Elementos de costo y documentos fuente", level=2)
add_table(
    ["Componente", "Tratamiento de costeo propuesto", "Evidencia mínima"],
    [
        ["Mano de obra directa", "Horas reales aprobadas por empleado, fecha, fase y orden, multiplicadas por una tarifa vigente con cargas laborales configuradas." , "Planilla, tarifa efectiva, registro de tiempo, aprobación del líder y conciliación de horas pagadas."],
        ["Servicios externos del título", "Imputar directamente si el contrato/entregable pertenece a un título y se recibe y acepta. Guardar derechos cedidos/licenciados." , "Documento tributario, contrato, comprobante de recepción, pago/retención y términos de propiedad intelectual."],
        ["Licencias y herramientas", "Directas cuando se compran o usan exclusivamente en un título; compartidas por pool según usuarios, horas o consumo." , "Factura/licencia, período de uso, usuarios, proyecto beneficiado y método de prorrateo."],
        ["Infraestructura y soporte técnico", "Costos indirectos de producción por pool; asignar con consumo medible de nube, compilación, pruebas o soporte." , "Factura y datos de uso; hoja de cálculo de la tasa y detalle por orden."],
        ["Administración, ventas y lanzamiento", "Gasto del período o análisis gerencial separado; no cargar a costo de inventario si no contribuye a producir el título." , "Planilla/contrato, factura, centro de costo y cuenta aprobada."],
        ["Pérdida anormal y retrabajo", "Identificar por causa y mostrar en variación/periodo; no ocultar dentro de la tasa normal de producción." , "Incidente, ticket, causa, horas y responsable de aprobación."],
    ],
    widths=[1.3, 3.0, 2.85],
    font_size=8.3,
)
doc.add_paragraph(
    "Los documentos internos discrepan sobre los servicios de arte, música y otros terceros: el catálogo y la selección del objeto los describen como directos, mientras una decisión posterior del requerimiento generado los lleva al gasto del período y prohíbe vincularlos a una orden. El módulo debe conservar el vínculo analítico con el proyecto cuando el servicio sea identificable; la cuenta financiera que corresponda se decide aparte según la política aprobada. No se debe perder el costo gerencial del título por el hecho de que el asiento se presente como gasto del período. [D2][D3][D4]"
)

doc.add_heading("4.4 Tasa y asignación de costos indirectos", level=2)
doc.add_paragraph(
    "No conviene agrupar todos los costos comunes en una sola base si tienen causas distintas. Cada pool tendrá presupuesto, base, período de vigencia, tasa, costos reales y ajuste al cierre. Fórmulas propuestas: tasa predeterminada del pool = costos indirectos presupuestados del pool / unidades presupuestadas de su base; indirecto aplicado a la orden = consumo real aprobado de la base por la orden x tasa vigente."
)
add_table(
    ["Pool posible", "Base causal sugerida", "Decisión requerida"],
    [
        ["Nube, almacenamiento y compilación", "Uso medido por proyecto: cómputo, almacenamiento o ejecución de builds." , "Obtener métricas de consumo por videojuego y período."],
        ["Herramientas compartidas", "Usuarios/puestos activos, licencias utilizadas o tiempo de uso." , "Separar licencias exclusivas de suscripciones generales."],
        ["Control de calidad compartido", "Horas de QA o pruebas por orden, si las horas no están clasificadas como directas." , "Evitar contar las mismas horas como directas e indirectas."],
        ["Servicios de apoyo al desarrollo", "Horas verificables del equipo de soporte o tickets por proyecto." , "Aprobar solo los costos que apoyen efectivamente producción."],
    ],
    widths=[1.8, 2.8, 2.55],
)
doc.add_paragraph(
    "Los porcentajes de 8% para administración y 6% para talento humano que aparecen en el ejemplo interno son hipótesis gerenciales, no tasas normativas. Deben justificarse con causa y datos, y presentarse aparte si representan costos corporativos. En inventarios, la NIIF para las PYMES excluye los gastos administrativos que no contribuyen a la condición del inventario y los costos de venta; los indirectos de producción se asignan sistemáticamente y los fijos se distribuyen sobre la capacidad normal. [3]"
)

doc.add_heading("4.5 Registro, corte y variaciones", level=2)
for text in [
    "Abrir la orden solo con alcance, presupuesto, responsable, centro de costo, etapa y clasificación del objeto aprobados.",
    "Registrar cada hora pagada una sola vez: directamente a una orden, como costo indirecto o como gasto del período. La suma de esas clasificaciones debe conciliar con la planilla.",
    "Capturar compras y servicios con proveedor, soporte, período, cuenta, orden cuando corresponda, IVA/retención y aprobación. Un documento duplicado no crea otro costo.",
    "Al cierre mensual, aplicar tasas vigentes únicamente a horas/uso aprobados, conciliar costos reales y aplicados por pool, y presentar sobreaplicación o subaplicación. La partida de liquidación queda en borrador hasta definir cuenta y contrapartida autorizadas.",
    "Cerrar la orden después de conciliar horas, documentos, entregables, costos asignados, variaciones y derechos de propiedad intelectual. Una orden cerrada no acepta movimientos retroactivos; las correcciones deben conservar vínculo y motivo.",
    "Generar hoja de costos por título, fase, empleado, centro, período y proveedor, con presupuesto original, presupuesto vigente, costo real, indirecto aplicado, variación y saldo acumulado.",
]:
    add_number(text)

doc.add_heading("5. Aplicación ilustrativa con información de SunGames", level=1)
doc.add_paragraph(
    "El documento interno de selección del objeto de costo incluye un ejemplo simulado para un título propio con ingresos estimados de US$61,000.00. Los importes siguientes no son datos contables reales de SunGames ni una estimación de expertos aprobada; sirven para mostrar cómo se presentaría el presupuesto por orden y qué debe validarse antes de usarlo. [D3]"
)
add_table(
    ["Concepto del ejemplo", "Base registrada", "US$"],
    [
        ["Equipo de desarrollo", "4,800 horas x US$6.00", "28,800.00"],
        ["Control de calidad", "600 horas x US$4.00", "2,400.00"],
        ["Motores y herramientas", "Licencias asignadas al título", "3,600.00"],
        ["Arte, animación y audio", "Fases/entregables aceptados", "5,000.00"],
        ["Costos directos", "Subtotal de conceptos directos", "39,800.00"],
        ["Administración y gerencia", "8% de nómina directa", "2,496.00"],
        ["Operaciones y logística", "4 hitos x US$300.00", "1,200.00"],
        ["Soporte técnico y entorno", "Uso de licencias/plataformas", "900.00"],
        ["Talento humano y planillas", "6% de nómina directa", "1,872.00"],
        ["Asignaciones compartidas", "Subtotal del ejemplo", "6,468.00"],
        ["Costo completo asignado", "Costos directos + asignaciones", "46,268.00"],
        ["Excedente sobre ingresos estimados", "US$61,000.00 - US$46,268.00", "14,732.00"],
    ],
    widths=[2.45, 3.45, 1.25],
)
doc.add_paragraph(
    "Lectura contable: US$46,268.00 puede presentarse como costo total gerencial asignado solo después de validar las horas, tarifas, facturas y bases indirectas. US$14,732.00 equivale al 24.15% de los ingresos estimados antes de comisiones de Steam, reembolsos, otros costos de venta e impuestos; por incluir cargas administrativas, debe llamarse excedente del proyecto después de asignaciones, no margen bruto financiero sin recalcular las categorías."
)
doc.add_paragraph(
    "Para un informe de producción, separar los US$4,368.00 atribuidos a administración/gerencia y talento humano como asignaciones corporativas; verificar si los US$1,200.00 de logística y los US$900.00 de soporte técnico contribuyen directamente a producir el título. Solo los costos atribuibles de producción forman parte del costo de inventario bajo la Sección 13. Las comisiones de Steam se muestran como costo/gasto de venta separado conforme a los importes reales del reporte de la plataforma. [3][5]"
)
doc.add_paragraph(
    "El ejemplo se convierte en una estimación por juicio de expertos cuando SunGames identifica a quienes fijaron las horas, las fases, las tarifas, el rango y los supuestos; registra su proceso de revisión y obtiene aprobación. El módulo debe distinguir esta versión estimada del costo real acumulado por la orden."
)

doc.add_heading("6. Marco normativo y efecto en la política contable", level=1)
add_table(
    ["Fuente", "Efecto en el costeo de SunGames", "Decisión o control"],
    [
        ["CVPCPA, Resolución 462; NIIF para las PYMES edición 2015 [1]", "La resolución pública ratifica la versión en español de 2015. La tercera edición IASB es efectiva para períodos desde 2027 y conserva la regla 18.14 sobre desembolsos internos, pero debe confirmarse su adopción local antes de usarla." , "Registrar edición, fecha de vigencia y acuerdo local aplicable a cada ejercicio."],
        ["NIIF para las PYMES Sección 13 [2][3]", "Los inventarios incluyen producción en curso para venta. El costo incorpora conversión y costos de producción atribuibles; los proyectos segregados usan identificación específica. Se excluyen administración no atribuible y ventas; el inventario se reconoce como gasto al reconocer el ingreso relacionado." , "Analizar si el título licenciado por Steam se produce y mantiene para la venta en el curso ordinario; documentar licencia, control y reconocimiento del costo."],
        ["NIIF para las PYMES Sección 18 [2]", "El párrafo 18.14 lleva a gasto los desembolsos internos de investigación y desarrollo para intangibles generados internamente, salvo que formen parte de otro activo que cumpla la norma. No debe aplicarse automáticamente a un producto que esté en inventarios bajo Sección 13." , "Separar título vendido/licenciado, software de uso interno y licencias de software adquiridas."],
        ["NIIF completas NIC 38 [4]", "Si SunGames formalmente adopta NIIF completas y el título se clasifica como intangible, los gastos de investigación se llevan a gasto y desarrollo solo se reconoce con todos los criterios de NIC 38.57; los costos se identifican desde la fecha en que se cumplen." , "No aplicar ASC 985-20 como autoridad contable local junto con NIIF para las PYMES; pedir aprobación del marco antes de fijar regla de capitalización."],
        ["Código de Comercio, arts. 435-436 [5]", "Exige contabilidad organizada, libros y documentos probatorios conservados; permite medios electrónicos idóneos y requiere registros en castellano y moneda admitida por ley." , "Cada costo se vincula a asiento, usuario, fecha, documento, orden y autorización."],
        ["Código Tributario, arts. 139 y 147 [6]", "La contabilidad formal debe seguir un método apropiado, libros autorizados, auxiliares y soporte legal; se conservan libros y comprobantes por diez años, incluidos datos y programas de contabilidad computarizada." , "Conservar hoja de costos, parámetros, código/versión del cálculo, evidencia y respaldos legibles por diez años."],
        ["Ley de Impuesto sobre la Renta, art. 30-A [7]", "Regula la deducción fiscal por amortización de software usado para producir renta gravable, con máximo anual del 25% y reglas específicas. No convierte ese máximo fiscal en vida útil contable automática." , "Separar auxiliar fiscal de la medición financiera; mantener referencias y vigencia de cada regla tributaria."],
        ["NASA, GAO y OpenStax [8][9][10][11]", "Son guías técnicas y académicas para estimar y acumular costos; no son obligaciones legales salvadoreñas. Recomiendan documentación, validación, bases de asignación y comparación con reales." , "Usarlas como sustento de diseño del procedimiento, no como norma de reconocimiento financiero."],
    ],
    widths=[1.7, 3.5, 1.95],
    font_size=8.1,
)
doc.add_paragraph(
    "Punto de decisión contable: el catálogo y los requerimientos actuales proponen cuentas para videojuegos en desarrollo/terminados y amortización, pero el manual menciona códigos 1106/1107 mientras la especificación de costos utiliza 1204/1205; además, el propio requerimiento generado deja la clasificación y capitalización pendientes y en ciertos reportes mantiene esos saldos como activos corrientes. Debe aprobarse una única correspondencia de cuentas y presentación, y eliminarse la contradicción entre inventario, intangible y activo corriente/no corriente antes de generar asientos automáticos. [D1][D2][D4]"
)
doc.add_paragraph(
    "El máximo fiscal de 25% anual del artículo 30-A es una regla de deducción tributaria para los programas informáticos que cumplan el supuesto legal. No determina por sí solo la vida útil contable ni crea una regla universal de cuatro años para videojuegos. La estimación de vida útil y el reconocimiento del costo del título siguen el marco contable aprobado y los términos del derecho/licencia; los efectos fiscales se concilian por separado. [7]"
)

doc.add_heading("7. Necesidades y requisitos recomendados para el módulo", level=1)
doc.add_paragraph(
    "Los siguientes requisitos complementan RF-16 a RF-20 y la especificación de órdenes de trabajo. Su finalidad es hacer verificable el presupuesto, el costo real y la decisión de presentación contable. Las tasas, cuentas, permisos y umbrales deben configurarse con vigencia y aprobación; no deben quedar codificados como constantes sin respaldo."
)
add_table(
    ["Requisito propuesto", "Necesidad funcional", "Aceptación mínima"],
    [
        ["RCC-07 Estimación por expertos", "Presupuestar horas y costos por fase, rol, riesgo y orden; versionar estimación y guardar supuestos, fuente, rango y revisiones." , "No se aprueba línea base si faltan alcance, método, estimadores, horas/tarifas, fecha, evidencia y aprobador. Estimación no contabiliza."],
        ["RCC-08 Orden y hoja de costos", "Orden única por título propio, contrato por encargo o mantenimiento, con fases, centros y estado." , "Cada movimiento y reporte identifica tipo de proyecto, orden, fase, período y estado."],
        ["RCC-09 Tiempo y conciliación", "Capturar horas por empleado y clasificarlas una sola vez como directas, indirectas o gasto del período." , "La planilla concilia con horas por clasificación; no se aceptan horas duplicadas ni órdenes cerradas."],
        ["RCC-10 Tarifas laborales", "Mantener tarifa por rol/persona y fecha; incluir conceptos de remuneración/cargas aprobados." , "Cada cálculo muestra tarifa efectiva y fuente. Si falta tarifa vigente, bloquea el costo real y señala el empleado/período."],
        ["RCC-11 Compras directas", "Asociar factura, proveedor, contrato, entrega aceptada, orden y derechos sobre contenido o código." , "Un documento no duplica importes; un servicio atribuible mantiene dimensión de orden aunque el asiento financiero sea gasto."],
        ["RCC-12 Pools indirectos", "Separar costos reales y presupuestados por pool, base, tasa, período y centro de servicio." , "El usuario puede reconstruir tasa e importe aplicado; cada pool tiene base aprobada y no aplica si su denominador es cero."],
        ["RCC-13 Cierre y variaciones", "Conciliar indirectos reales/aplicados y horas/tarifas/presupuesto; guardar sub/sobreaplicación." , "Variación identifica signo, método, evidencia y cuenta de liquidación configurada; no se genera partida con cuenta pendiente."],
        ["RCC-14 Tratamiento contable", "Versionar por título la política Sección 13, 18 o 23 según clasificación aprobada; mapear a cuenta y corte." , "Sin política/cuenta aprobada, conserva costeo analítico, bloquea traslado/capitalización/amortización."],
        ["RCC-15 Reportes y auditoría", "Emitir hoja por orden, fase, centro, período y tercero, con presupuesto, real, aplicado y variaciones." , "Totales concilian con auxiliar y mayor; exportación PDF/XLSX conserva filtros, moneda, versión y trazabilidad."],
        ["RCC-16 Acceso y conservación", "Restringir aprobación, captura y cambios; preservar bitácora y documentos fuente." , "Se registra usuario, fecha, evidencia y motivo. Respaldo y conservación cumplen política y plazo legal aplicable."],
    ],
    widths=[1.45, 2.85, 2.85],
    font_size=8.0,
)

doc.add_heading("8. Controles internos y seguridad vinculados", level=1)
doc.add_paragraph(
    "Los controles propuestos responden a RNF-01 a RNF-07 y RNF-16 a RNF-20. El contador de costos prepara o registra; el responsable de proyecto aprueba horas y entregables; el administrador mantiene cuentas, tarifas y reglas; y la Junta Directiva aprueba la política contable, presupuesto y cambios relevantes. Si el personal disponible obliga a combinar funciones, el sistema exige una revisión independiente antes del asiento/cierre."
)
for text in [
    "Conservar bitácora no editable con cambios de presupuesto, tarifas, horas, bases indirectas, órdenes, cuentas y tratamiento contable.",
    "Asociar cada costo a un documento fuente o una evidencia operativa; permitir reconstruir importe, período, orden, tasa aplicada, cuenta y aprobación.",
    "Impedir alteraciones de costos contabilizados; corregir con reversa o ajuste vinculado al registro original.",
    "Controlar acceso por rol y separar configuración del Administrador de las operaciones y reportes del Contador de costos.",
    "Exportar en castellano y USD, con dos decimales cuando corresponda, y conservar respaldo, restauración y evidencia de auditoría.",
]:
    add_bullet(text)
doc.add_paragraph(
    "ISO 27001, COSO e ISO 22301 y las NIA mencionadas en los requerimientos son referencias de control, evidencia, riesgo y continuidad; por sí solas no fijan la medición del costo ni sustituyen las NIIF, el Código de Comercio o el Código Tributario. Deben tratarse como marcos de diseño o auditoría según la decisión de SunGames, no como una obligación adicional presumida. [D1]"
)

doc.add_heading("9. Decisiones que deben cerrarse antes de programar los asientos", level=1)
add_table(
    ["Decisión", "Propuesta técnica para resolverla", "Efecto si queda abierta"],
    [
        ["Clasificación del título propio", "Emitir memorando que compare Sección 13 (producto/inventario producido para licencia/venta) con Sección 18 (intangible no mantenido para venta) y revise contrato con Steam y derechos del juego." , "No trasladar los costos a activo ni calcular amortización/costo de ventas automáticamente."],
        ["Edición NIIF aplicable", "Aprobar edición adoptada localmente y fecha de aplicación. CVPCPA confirma públicamente edición 2015; la tercera edición IASB inicia en 2027 con adopción anticipada permitida por el IASB." , "Evita usar una edición internacional sin aprobación local."],
        ["Catálogo y clasificación", "Armonizar 1106/1107 con 1204/1205, denominación y rubro; eliminar activo corriente/no corriente incompatible con el ciclo operativo y la política." , "Reportes no concilian entre manual, mayor y módulo."],
        ["Servicios de terceros", "Aprobar criterio común para 4102/4502 y guardar orden analítica cuando arte, música, audio o QA se atribuyan a un juego." , "La hoja de costos omite componentes de un título o los duplica."],
        ["Pools y bases indirectas", "Validar cada pool; usar consumo/hora de uso/horas de trabajo o hitos con relación causal. Revisar 8% y 6% del ejemplo." , "La tasa puede distorsionar el costo por juego y el valor de inventario."],
        ["Tarifas de costo laboral", "Configurar remuneración y cargas por rol/fecha y denominador de horas productivas aprobado por planilla y contabilidad." , "El costo por hora no es reproducible o se omiten obligaciones aplicables."],
        ["Liquidación de indirectos", "Definir cuentas y contrapartida para subaplicación/sobreaplicación y quién aprueba la partida." , "Variación calculada sin asiento válido o con clasificación errónea."],
        ["Vida útil y fiscalidad", "Definir vida útil contable por evidencia comercial; auxiliar fiscal separado para LISR 30-A, máximo legal y demás condiciones." , "La tasa fiscal se confunde con la amortización de estados financieros."],
    ],
    widths=[1.45, 3.55, 2.15],
    font_size=8.0,
)

doc.add_heading("10. Ruta de implementación", level=1)
add_table(
    ["Etapa", "Producto de trabajo", "Salida de control"],
    [
        ["1. Aprobación contable", "Memorando de clasificación del título propio y servicio por encargo; edición NIIF; catálogo y cuentas." , "Política firmada y matriz cuenta-tratamiento vigente."],
        ["2. Preparación de datos", "Maestro de proyectos, fases, roles, tarifas, proveedores, licencias, pools y bases." , "Datos iniciales documentados y aprobados."],
        ["3. Estimación inicial", "Estimación de expertos para SG-TIT-01 por fases/roles y línea base autorizada." , "Acta/registro de estimación versionado."],
        ["4. Costeo piloto", "Captura de tiempos, compras, órdenes, indirectos y reporte de variaciones durante un período." , "Conciliación con planilla, documentos, mayor y datos de plataforma."],
        ["5. Cierre y revisión", "Prueba de cierre, costeo por orden, variación, exportación y restauración de respaldos." , "Aprobación del contador y de la instancia definida antes de activar asientos automáticos."],
    ],
    widths=[1.35, 3.6, 2.2],
)

doc.add_heading("Conclusión", level=1)
doc.add_paragraph(
    "Para SunGames, el juicio de expertos debe establecer una línea base trazable de esfuerzo y presupuesto para cada videojuego. El costeo por órdenes de trabajo debe acumular después las horas, compras y costos indirectos reales por título, fase y contrato. La combinación sirve para presupuestar, controlar desviaciones y conocer el costo total por juego, incluso si la política financiera reconoce ciertos desembolsos como gasto del período."
)
doc.add_paragraph(
    "La decisión crítica es de clasificación contable: el título licenciado mediante Steam debe analizarse primero como producto en proceso/terminado para venta bajo Sección 13 o, si los hechos muestran un intangible no mantenido para venta, bajo Sección 18 y/o la norma de ingresos aplicable. Esa conclusión determina las cuentas, exclusiones, reconocimiento de costos y tratamiento de amortización. Por tanto, conviene implementar de inmediato el auxiliar por órdenes y el registro del juicio experto, pero condicionar cualquier asiento automático de capitalización, traslado o amortización a la política formal y al catálogo armonizado."
)

doc.add_heading("Referencias normativas y técnicas", level=1)
references = [
    ("1", "Consejo de Vigilancia de la Profesión de Contaduría Pública y Auditoría (CVPCPA). Resolución 462, 18 de marzo de 2021; ratifica NIIF para las PYMES, versión español 2015.", "https://www.cvpcpa.gob.sv/download/resolucion-462/"),
    ("2", "IFRS Foundation. IFRS for SMEs Accounting Standard, Third Edition (2025), Sections 13 and 18; Section 18.14 and Appendix A, effective date.", "https://www.ifrs.org/content/dam/ifrs/supporting-implementation/smes/2025/ifrs-for-smes-standard-markup.pdf"),
    ("3", "IFRS Foundation. IFRS for SMEs Educational Module 18, Intangible Assets other than Goodwill (2026); paragraphs 18.14-18.15.", "https://www.ifrs.org/content/dam/ifrs/supporting-implementation/smes/2026-modules/module-18.pdf"),
    ("4", "IFRS Foundation. IAS 38 Intangible Assets, paragraphs 54-58; research and development phases and criteria for development recognition.", "https://www.ifrs.org/content/dam/ifrs/publications/pdf-standards/english/2022/issued/part-a/ias-38-intangible-assets.pdf?bypass=on"),
    ("5", "República de El Salvador. Código de Comercio, artículos 435-436; Biblioteca de la Asamblea Legislativa / texto legislativo.", "https://www.uif.gob.sv/wp-content/uploads/leyes/Codigo-de-Comercio.pdf"),
    ("6", "República de El Salvador. Código Tributario, artículos 139 y 147; compilación del Portal de Transparencia Fiscal.", "https://www.transparenciafiscal.gob.sv/downloads/pdf/DC5810_Codigo_Tributario_con_reformas_a_noviembre_de_2015.pdf"),
    ("7", "República de El Salvador. Ley de Impuesto sobre la Renta, texto actualizado al Diario Oficial No. 79, tomo 447, 30 de abril de 2025; artículo 30-A.", "https://sitio.aduana.gob.sv/wp-content/uploads/download-manager-files/LEY-DE-IMPUESTO-SOBRE-LA-RENTA-ACTUALIZADA-CON-EL-D.-O.-N%C2%B0-79-T.-447-30-DE-ABRIL-DE-2025.pdf"),
    ("8", "NASA. Handbook for Software Cost Estimation; estimating methods, including expert judgment and historical analogy.", "https://swehb.nasa.gov/download/attachments/16450436/Handbook_for_Software_Cost_Estimation.pdf?api=v2"),
    ("9", "NASA Marshall Space Flight Center. Project Planning and Control Handbook, MSFC-HDBK-3684A (2017); expert opinion/Delphi approach.", "https://standards.nasa.gov/sites/default/files/standards/MSFC/A/0/msfchdbk3684a.pdf"),
    ("10", "U.S. Government Accountability Office (GAO). Cost Estimating and Assessment Guide, GAO-20-195G (2020); documentation, validation, uncertainty and updates with actuals.", "https://www.gao.gov/products/gao-20-195g"),
    ("11", "Rice University, OpenStax. Principles of Accounting, Volume 2: Managerial Accounting, Chapter 4; job order cost sheets, direct labor and overhead allocation.", "https://openstax.org/books/principles-managerial-accounting/pages/4-5-compute-the-cost-of-a-job-using-job-order-costing"),
]
for number, citation, url in references:
    add_ref(number, citation, url)

doc.add_heading("Documentos internos de SunGames revisados", level=1)
internal_refs = [
    "[D1] Requerimientos funcionales y no funcionales del sistema contable, carpeta Requerimientos.",
    "[D2] Especificación de Requerimientos de Software SunGames, carpeta Requerimientos/generados.",
    "[D3] Contabilidad de Costos: Selección y Justificación del Producto o Servicio; Diseño Contable, Políticas, Documentos Fuente y Flujo de Información.",
    "[D4] Manual de aplicación del catálogo SunGames y decisiones de diseño incorporadas en la especificación generada.",
    "[D5] Modelo de negocio SunGames y caracterización empresarial disponibles en el proyecto.",
]
for item in internal_refs:
    p = doc.add_paragraph(item)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.paragraph_format.space_after = Pt(3)

# Footer with page number; no decorative header.
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer.paragraph_format.space_before = Pt(4)
r = footer.add_run("SunGames S.A. de C.V.  |  Contabilidad de costos  |  ")
r.font.name = "Arial"
r.font.size = Pt(8)
r.font.color.rgb = RGBColor.from_string("666666")
add_page_field(footer)

# Set document metadata to the organization rather than the build script author.
doc.core_properties.title = "Investigación y aplicación de métodos de costeo para SunGames S.A. de C.V."
doc.core_properties.subject = "Juicio de expertos y órdenes de trabajo en contabilidad de costos"
doc.core_properties.author = "SunGames S.A. de C.V."
doc.core_properties.keywords = "contabilidad de costos, videojuegos, juicio de expertos, órdenes de trabajo, NIIF para las PYMES"

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
