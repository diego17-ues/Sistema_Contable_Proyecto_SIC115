from django.test import SimpleTestCase
from django.utils import timezone

from bitacora.eventos import Accion, Resultado
from bitacora.exceptions import FormatoNoSoportadoError, SinEventosError
from bitacora.exportadores import (
    ExportadorExcel,
    ExportadorPDF,
    FabricaExportadores,
)
from bitacora.models import RegistroBitacora
from bitacora.services import AuditoriaService
from usuarios.exceptions import RolNoAutorizadoError
from usuarios.models import Usuario
from usuarios.roles import Rol


class BitacoraRepositoryEnMemoria:
    def __init__(self, eventos=()):
        self.eventos = list(eventos)

    def listar(self):
        return list(self.eventos)


class FabricaFalsa:
    def __init__(self):
        self.formatos = []

    def crear(self, formato):
        self.formatos.append(formato)
        return FabricaExportadores().crear(formato)


def crear_evento():
    return RegistroBitacora(
        fecha_hora=timezone.now(),
        actor=Usuario(username="admin", rol=Rol.ADMINISTRADOR),
        accion=Accion.INICIO_SESION, resultado=Resultado.EXITOSO,
    )


class AuditoriaServiceTests(SimpleTestCase):
    def setUp(self):
        self.admin = Usuario(username="admin", rol=Rol.ADMINISTRADOR)
        self.contador = Usuario(username="cont", rol=Rol.CONTADOR_GENERAL)
        self.fabrica = FabricaFalsa()

    def servicio(self, eventos=()):
        return AuditoriaService(
            BitacoraRepositoryEnMemoria(eventos), self.fabrica
        )

    def test_listado_vacio(self):
        self.assertEqual(list(self.servicio().listar(self.admin)), [])

    def test_listado_exige_administrador(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio().listar(self.contador)

    def test_exportar_exige_administrador(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio([crear_evento()]).exportar(self.contador, "pdf")

    def test_exportar_sin_eventos_informa(self):
        with self.assertRaises(SinEventosError):
            self.servicio().exportar(self.admin, "pdf")

    def test_exportar_formato_no_soportado(self):
        with self.assertRaises(FormatoNoSoportadoError):
            self.servicio([crear_evento()]).exportar(self.admin, "csv")

    def test_exportar_usa_la_estrategia_de_la_fabrica(self):
        archivo = self.servicio([crear_evento()]).exportar(
            self.admin, "excel"
        )

        self.assertEqual(self.fabrica.formatos, ["excel"])
        self.assertEqual(
            archivo.tipo_contenido, ExportadorExcel.tipo_contenido
        )
        self.assertTrue(archivo.contenido)


class FabricaExportadoresTests(SimpleTestCase):
    def test_elige_la_estrategia_por_formato(self):
        fabrica = FabricaExportadores()

        self.assertIsInstance(fabrica.crear("pdf"), ExportadorPDF)
        self.assertIsInstance(fabrica.crear("excel"), ExportadorExcel)

    def test_pdf_genera_un_documento(self):
        archivo = ExportadorPDF().exportar([crear_evento()])

        self.assertTrue(archivo.contenido.startswith(b"%PDF"))
        self.assertTrue(archivo.nombre.endswith(".pdf"))
