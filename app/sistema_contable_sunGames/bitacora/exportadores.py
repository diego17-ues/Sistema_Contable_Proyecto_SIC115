"""Estrategias de exportación de la bitácora (CU-03.2)."""

from dataclasses import dataclass
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from .exceptions import FormatoNoSoportadoError

ENCABEZADOS = (
    "Fecha y hora", "Usuario actor", "Usuario afectado", "Acción",
    "Resultado", "Detalle",
)
# TODO(CU-03.2): el nombre de archivo y la plantilla de los reportes no
# están definidos en la especificación; se usa un nombre provisional.
NOMBRE_BASE_ARCHIVO = "bitacora_auditoria"
FORMATO_FECHA_HORA = "%d/%m/%Y %H:%M:%S"


@dataclass(frozen=True)
class ArchivoExportado:
    contenido: bytes
    tipo_contenido: str
    nombre: str


def accion_con_referencia(evento):
    accion = evento.get_accion_display()
    return f"{accion} · {evento.referencia}" if evento.referencia else accion


def filas(eventos):
    for evento in eventos:
        yield (
            timezone.localtime(evento.fecha_hora).strftime(FORMATO_FECHA_HORA),
            evento.actor.username if evento.actor_id else "",
            evento.afectado.username if evento.afectado_id else "",
            accion_con_referencia(evento),
            evento.get_resultado_display(),
            evento.detalle,
        )


class Exportador:
    """Interfaz común de las estrategias de exportación."""

    tipo_contenido = ""
    extension = ""

    def exportar(self, eventos):
        return ArchivoExportado(
            contenido=self._generar(eventos),
            tipo_contenido=self.tipo_contenido,
            nombre=f"{NOMBRE_BASE_ARCHIVO}.{self.extension}",
        )

    def _generar(self, eventos):
        raise NotImplementedError


class ExportadorPDF(Exportador):
    """CU-03.2.1 Descargar PDF."""

    tipo_contenido = "application/pdf"
    extension = "pdf"

    def _generar(self, eventos):
        buffer = BytesIO()
        documento = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        tabla = Table([ENCABEZADOS, *filas(eventos)], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102b45")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        titulo = Paragraph(
            "Bitácora de auditoría", getSampleStyleSheet()["Title"]
        )
        documento.build([titulo, tabla])
        return buffer.getvalue()


class ExportadorExcel(Exportador):
    """CU-03.2.2 Descargar Excel: una fila por evento."""

    tipo_contenido = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    extension = "xlsx"

    def _generar(self, eventos):
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Bitácora"
        hoja.append(ENCABEZADOS)
        for fila in filas(eventos):
            hoja.append(fila)
        buffer = BytesIO()
        libro.save(buffer)
        return buffer.getvalue()


class FabricaExportadores:
    """Elige la estrategia de exportación según el formato solicitado."""

    def __init__(self, exportadores=None):
        self._exportadores = exportadores or {
            "pdf": ExportadorPDF,
            "excel": ExportadorExcel,
        }

    def crear(self, formato):
        try:
            return self._exportadores[formato]()
        except KeyError as exc:
            raise FormatoNoSoportadoError() from exc
