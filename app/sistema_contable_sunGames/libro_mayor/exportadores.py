"""PDF del Balance de comprobación (CU-04.1) con formato de estado contable."""

from dataclasses import dataclass
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

EMPRESA = "SunGames S.A. de C.V."
AZUL = colors.HexColor("#102b45")
DORADO = colors.HexColor("#f4b63a")
GRIS = colors.HexColor("#f3f5f8")
LINEA = colors.HexColor("#c9d1dc")
VERDE = colors.HexColor("#1e7b4f")
ROJO = colors.HexColor("#b42318")

ESTILO_EMPRESA = ParagraphStyle(
    "empresa", fontName="Helvetica-Bold", fontSize=13, leading=16,
    alignment=TA_CENTER, textColor=AZUL,
)
ESTILO_TITULO = ParagraphStyle(
    "titulo", fontName="Helvetica-Bold", fontSize=15, leading=19,
    alignment=TA_CENTER, textColor=AZUL, spaceBefore=2,
)
ESTILO_SUBTITULO = ParagraphStyle(
    "subtitulo", fontName="Helvetica", fontSize=9.5, leading=13,
    alignment=TA_CENTER, textColor=colors.HexColor("#4a5a6b"),
)
ESTILO_CELDA = ParagraphStyle(
    "celda", fontName="Helvetica", fontSize=9, leading=10
)
ESTILO_ESTADO = ParagraphStyle(
    "estado", fontName="Helvetica-Bold", fontSize=10, leading=13,
    alignment=TA_RIGHT,
)


@dataclass(frozen=True)
class ArchivoExportado:
    contenido: bytes
    tipo_contenido: str
    nombre: str


def dinero(valor):
    return f"${valor:,.2f}" if valor else "—"


class ExportadorBalancePDF:
    tipo_contenido = "application/pdf"
    ANCHOS = (22 * mm, 102 * mm, 31 * mm, 31 * mm)

    def __init__(self, logo=None, comprimir=True):
        self._logo = logo
        self._comprimir = comprimir

    def exportar(self, balance, usuario):
        buffer = BytesIO()
        corte = balance.fecha_corte.strftime("%d/%m/%Y")
        generado = timezone.localtime().strftime("%d/%m/%Y %H:%M")
        documento = SimpleDocTemplate(
            buffer, pagesize=letter, title="Balance de Comprobación",
            author=EMPRESA, leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=16 * mm, bottomMargin=18 * mm,
            pageCompression=1 if self._comprimir else 0,
        )
        pie = f"Generado el {generado} por {usuario.username}"

        def numerar(lienzo, doc):
            lienzo.saveState()
            lienzo.setFont("Helvetica", 7.5)
            lienzo.setFillColor(colors.HexColor("#6b7785"))
            lienzo.drawString(doc.leftMargin, 10 * mm, pie)
            lienzo.drawRightString(
                letter[0] - doc.rightMargin, 10 * mm,
                f"Página {doc.page}",
            )
            lienzo.restoreState()

        documento.build(
            [*self._encabezado(corte), self._tabla(balance), Spacer(1, 8),
             self._estado(balance)],
            onFirstPage=numerar, onLaterPages=numerar,
        )
        return ArchivoExportado(
            contenido=buffer.getvalue(),
            tipo_contenido=self.tipo_contenido,
            nombre=f"balance_comprobacion_{balance.fecha_corte:%Y%m%d}.pdf",
        )

    def _encabezado(self, corte):
        textos = [
            Paragraph(EMPRESA, ESTILO_EMPRESA),
            Paragraph("Balance de Comprobación", ESTILO_TITULO),
            Paragraph(f"Al {corte}", ESTILO_SUBTITULO),
            Paragraph("Expresado en dólares de los Estados Unidos (USD)",
                      ESTILO_SUBTITULO),
        ]
        logo = Image(self._logo, width=45 * mm, height=15 * mm) \
            if self._logo else ""
        encabezado = Table(
            [[logo, textos, ""]], colWidths=(46 * mm, 94 * mm, 46 * mm)
        )
        encabezado.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, DORADO),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ]))
        return [encabezado, Spacer(1, 12)]

    def _tabla(self, balance):
        filas = [["Código", "Cuenta", "Debe", "Haber"]]
        for fila in balance.filas:
            filas.append([
                fila.cuenta.codigo,
                Paragraph(fila.cuenta.denominacion, ESTILO_CELDA),
                dinero(fila.debe), dinero(fila.haber),
            ])
        if not balance.filas:
            filas.append(["", "Sin movimientos a la fecha de corte", "", ""])
        filas.append([
            "", "Totales", f"${balance.total_debe:,.2f}",
            f"${balance.total_haber:,.2f}",
        ])
        ultima = len(filas) - 1
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 1), (-1, ultima - 1), 0.4, LINEA),
            ("FONTNAME", (0, ultima), (-1, ultima), "Helvetica-Bold"),
            ("LINEABOVE", (0, ultima), (-1, ultima), 1, AZUL),
            ("LINEBELOW", (2, ultima), (-1, ultima), 2.2, AZUL),
            ("LINEBELOW", (2, ultima), (-1, ultima), 0.6, colors.white),
        ]
        estilo += [
            ("BACKGROUND", (0, indice), (-1, indice), GRIS)
            for indice in range(2, ultima, 2)
        ]
        tabla = Table(filas, colWidths=self.ANCHOS, repeatRows=1)
        tabla.setStyle(TableStyle(estilo))
        return tabla

    @staticmethod
    def _estado(balance):
        if balance.balanceado:
            texto, color = "Balanceado: Debe y Haber coinciden.", VERDE
        else:
            texto = (
                f"Diferencia entre Debe y Haber: "
                f"${abs(balance.diferencia):,.2f}"
            )
            color = ROJO
        return Paragraph(
            texto, ParagraphStyle("estado_color", parent=ESTILO_ESTADO,
                                  textColor=color)
        )
