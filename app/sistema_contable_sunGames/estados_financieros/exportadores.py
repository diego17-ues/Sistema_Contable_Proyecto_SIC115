"""PDF de estados financieros con la presentación de NIC 1."""

from decimal import Decimal
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
from reportlab.platypus import TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT

from libro_mayor.exportadores import (
    AZUL,
    DORADO,
    EMPRESA,
    GRIS,
    LINEA,
    ROJO,
    VERDE,
    ArchivoExportado,
)

from .formato import cifra
from .models import TipoEstado

MONEDA = "Expresado en dólares de los Estados Unidos de América (USD)"
NOTA = (
    "Presentación conforme a NIC 1. Cifras en USD con dos decimales; "
    "los valores negativos se muestran entre paréntesis."
)
NOMBRES_ARCHIVO = {
    TipoEstado.BALANCE_GENERAL: "balance_general",
    TipoEstado.ESTADO_RESULTADOS: "estado_resultados",
}
SECCION = colors.HexColor("#e8edf3")


class ExportadorEstadoPDF:
    tipo_contenido = "application/pdf"
    ANCHOS = (18 * mm, 120 * mm, 38 * mm)

    def __init__(self, logo=None, comprimir=True):
        self._logo = logo
        self._comprimir = comprimir

    def exportar(self, datos, *, estado_periodo, fecha_emision=None):
        emision = timezone.localtime(fecha_emision or timezone.now())
        buffer = BytesIO()
        documento = SimpleDocTemplate(
            buffer, pagesize=letter, title=datos["titulo"], author=EMPRESA,
            leftMargin=20 * mm, rightMargin=20 * mm, topMargin=52 * mm,
            bottomMargin=26 * mm,
            pageCompression=1 if self._comprimir else 0,
        )
        pie = (f"Fecha de emisión: {emision:%d/%m/%Y %H:%M} · Estado del "
               f"período: {estado_periodo}")

        def pagina(lienzo, doc):
            self._encabezado(lienzo, doc, datos)
            self._pie(lienzo, doc, pie)

        contenido = [self._tabla(datos)]
        if datos["tipo"] == TipoEstado.BALANCE_GENERAL:
            contenido += [Spacer(1, 10), self._cuadre(datos)]
        documento.build(contenido, onFirstPage=pagina, onLaterPages=pagina)
        return ArchivoExportado(
            contenido=buffer.getvalue(), tipo_contenido=self.tipo_contenido,
            nombre=f"{NOMBRES_ARCHIVO[datos['tipo']]}_"
                   f"{datos['hasta'].replace('-', '')}.pdf",
        )

    def _encabezado(self, lienzo, doc, datos):
        ancho, alto = letter
        centro = ancho / 2
        lienzo.saveState()
        if self._logo:
            lienzo.drawImage(self._logo, doc.leftMargin, alto - 17 * mm,
                             width=30 * mm, height=10 * mm, mask="auto")
        lineas = (
            ("Helvetica-Bold", 13, AZUL, EMPRESA),
            ("Helvetica-Bold", 14, AZUL, datos["titulo"]),
            ("Helvetica", 10, colors.HexColor("#4a5a6b"), datos["cubre"]),
            ("Helvetica", 9, colors.HexColor("#4a5a6b"), MONEDA),
        )
        y = alto - 20 * mm
        for fuente, tamano, color, texto in lineas:
            lienzo.setFont(fuente, tamano)
            lienzo.setFillColor(color)
            lienzo.drawCentredString(centro, y, texto)
            y -= tamano + 5
        lienzo.setStrokeColor(DORADO)
        lienzo.setLineWidth(1.5)
        lienzo.line(doc.leftMargin, alto - 44 * mm,
                    ancho - doc.rightMargin, alto - 44 * mm)
        lienzo.restoreState()

    @staticmethod
    def _pie(lienzo, doc, pie):
        ancho, _ = letter
        lienzo.saveState()
        lienzo.setStrokeColor(LINEA)
        lienzo.line(doc.leftMargin, 18 * mm, ancho - doc.rightMargin, 18 * mm)
        lienzo.setFillColor(colors.HexColor("#6b7785"))
        lienzo.setFont("Helvetica", 7.5)
        lienzo.drawString(doc.leftMargin, 13 * mm, pie)
        lienzo.drawRightString(ancho - doc.rightMargin, 13 * mm,
                               f"Página {doc.page}")
        lienzo.drawString(doc.leftMargin, 9 * mm, NOTA)
        lienzo.restoreState()

    def _tabla(self, datos):
        filas = [["Código", "Concepto", "USD"]]
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]
        for indice, item in enumerate(datos["filas"], start=1):
            importe = item["importe"]
            filas.append([item["codigo"], item["texto"],
                          "" if importe is None else cifra(importe)])
            estilo += self._estilo_fila(indice, item["clase"])
        tabla = Table(filas, colWidths=self.ANCHOS, repeatRows=1)
        tabla.setStyle(TableStyle(estilo))
        return tabla

    @staticmethod
    def _estilo_fila(i, clase):
        negrita = ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")
        if clase == "seccion":
            return [negrita, ("BACKGROUND", (0, i), (-1, i), SECCION),
                    ("TEXTCOLOR", (0, i), (-1, i), AZUL),
                    ("FONTSIZE", (0, i), (-1, i), 10)]
        if clase == "grupo":
            return [negrita, ("LEFTPADDING", (1, i), (1, i), 10),
                    ("TEXTCOLOR", (0, i), (-1, i), AZUL)]
        if clase == "cuenta":
            return [("LEFTPADDING", (1, i), (1, i), 20)]
        if clase == "subtotal":
            return [negrita, ("LEFTPADDING", (1, i), (1, i), 10),
                    ("LINEABOVE", (2, i), (2, i), 0.6, colors.black)]
        if clase == "total":
            return [negrita, ("BACKGROUND", (0, i), (-1, i), GRIS),
                    ("LINEABOVE", (2, i), (2, i), 0.8, colors.black)]
        return [negrita, ("FONTSIZE", (0, i), (-1, i), 10),
                ("LINEABOVE", (0, i), (-1, i), 1, AZUL),
                ("LINEBELOW", (2, i), (2, i), 2.2, AZUL),
                ("LINEBELOW", (2, i), (2, i), 0.6, colors.white)]

    @staticmethod
    def _cuadre(datos):
        if datos["cuadra"]:
            texto, color = "Activo = Pasivo + Patrimonio: cuadra.", VERDE
        else:
            texto = ("Activo = Pasivo + Patrimonio: no cuadra; diferencia "
                     f"{cifra(Decimal(datos['diferencia']))}.")
            color = ROJO
        return Paragraph(texto, ParagraphStyle(
            "cuadre", fontName="Helvetica-Bold", fontSize=9.5,
            alignment=TA_RIGHT, textColor=color,
        ))
