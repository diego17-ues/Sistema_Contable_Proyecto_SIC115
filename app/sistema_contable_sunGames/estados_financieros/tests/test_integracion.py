import secrets
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from bitacora.eventos import Accion, Resultado
from bitacora.models import RegistroBitacora
from catalogo.models import Cuenta
from estados_financieros.exceptions import (
    EstadoInmutableError,
    GuardadoCierreError,
)
from estados_financieros.models import EstadoFinancieroEmitido
from estados_financieros.repositories import EstadosFinancierosRepository
from libro_mayor.exceptions import MovimientoInvalidoError, PeriodoCerradoError
from libro_mayor.models import (
    EstadoPeriodo,
    Movimiento,
    PeriodoContable,
    Transaccion,
)
from usuarios.models import Usuario
from usuarios.roles import Rol

CLAVE = secrets.token_urlsafe(12)
NOMBRE = "Ejercicio 2026"


class CierreIntegracionTests(TestCase):
    def setUp(self):
        self.contador = self.usuario("cont", Rol.CONTADOR_GENERAL)
        self.admin = self.usuario("admin", Rol.ADMINISTRADOR)
        self.periodo = PeriodoContable.objects.get(nombre=NOMBRE)
        self.transaccion = Transaccion.objects.create(usuario=self.contador)
        for codigo, importe in (("1101", "1500"), ("3101", "-1000"),
                                ("5101", "-800"), ("4201", "300")):
            self.movimiento(codigo, importe)

    def usuario(self, username, rol, activo=True):
        usuario = Usuario(username=username, nombre_completo="Ana", rol=rol,
                          activo=activo)
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def movimiento(self, codigo, importe, tipo="DIARIO"):
        return Movimiento.objects.create(
            transaccion=self.transaccion,
            cuenta=Cuenta.objects.get(codigo=codigo), fecha="2026-11-03",
            concepto="Operación", tipo=tipo, importe=Decimal(importe),
        )

    def cerrar(self, confirmacion=NOMBRE, motivo="Cierre de noviembre"):
        prefijo = f"p{self.periodo.pk}"
        return self.client.post(
            reverse("periodo_cerrar", args=[self.periodo.pk]),
            {f"{prefijo}-confirmacion": confirmacion,
             f"{prefijo}-motivo": motivo},
        )

    def reabrir(self, contrasena=CLAVE, motivo="Ajuste tardío"):
        prefijo = f"p{self.periodo.pk}"
        return self.client.post(
            reverse("periodo_reabrir", args=[self.periodo.pk]),
            {f"{prefijo}-contrasena": contrasena,
             f"{prefijo}-motivo": motivo},
        )

    def cerrar_como_contador(self):
        self.client.force_login(self.contador)
        self.assertRedirects(self.cerrar(), reverse("cierre_periodos"))
        self.periodo.refresh_from_db()

    def eventos(self, accion):
        return RegistroBitacora.objects.filter(accion=accion)

    def test_pantalla_muestra_modal_html_de_cierre(self):
        self.client.force_login(self.contador)

        pantalla = self.client.get(reverse("cierre_periodos"))

        for texto in (f'data-modal="cerrar-{self.periodo.pk}"',
                      f"Escribe «{NOMBRE}» para confirmar", "Motivo",
                      "Partidas incluidas", "Movimientos incluidos",
                      "Cuadra", "dejará de aceptar transacciones",
                      ">Cancelar</button>", ">Cerrar período</button>"):
            self.assertContains(pantalla, texto)
        self.assertNotContains(pantalla, "confirm(")

    def test_movimiento_en_periodo_cerrado_se_rechaza(self):
        existente = Movimiento.objects.first()
        self.cerrar_como_contador()

        with self.assertRaises(PeriodoCerradoError):
            self.movimiento("1101", "10")
        with self.assertRaises(PeriodoCerradoError):
            self.movimiento("1101", "10", tipo="AJUSTE")
        existente.concepto = "Cambiado"
        with self.assertRaises(PeriodoCerradoError):
            existente.save()
        with self.assertRaises(ValidationError):
            existente.full_clean()
        with self.assertRaises(PeriodoCerradoError):
            existente.delete()
        with self.assertRaises(MovimientoInvalidoError):
            Movimiento.objects.filter(pk=existente.pk).update(concepto="X")
        with self.assertRaises(MovimientoInvalidoError):
            Movimiento.objects.filter(pk=existente.pk).delete()
        self.assertEqual(Movimiento.objects.count(), 4)
        self.assertEqual(Movimiento.objects.get(pk=existente.pk).concepto,
                         "Operación")

    def test_estado_de_periodo_cerrado_no_cambia_fuera_de_la_reapertura(self):
        self.cerrar_como_contador()
        self.periodo.estado = EstadoPeriodo.ABIERTO

        with self.assertRaises(PeriodoCerradoError):
            self.periodo.save()
        self.periodo.refresh_from_db()
        self.assertTrue(self.periodo.cerrado)

    def test_snapshot_es_inmutable(self):
        self.cerrar_como_contador()
        emitido = EstadoFinancieroEmitido.objects.first()

        with self.assertRaises(EstadoInmutableError):
            emitido.save()
        with self.assertRaises(EstadoInmutableError):
            emitido.delete()
        with self.assertRaises(EstadoInmutableError):
            EstadoFinancieroEmitido.objects.update(datos={})

    def test_comando_calcula_abierto_y_rechaza_cerrado(self):
        salida = StringIO()
        call_command("estados_financieros", NOMBRE, stdout=salida)
        self.assertIn("TOTAL ACTIVO", salida.getvalue())
        self.assertIn("Patrimonio: cuadra", salida.getvalue())

        self.cerrar_como_contador()
        with self.assertRaisesMessage(CommandError, "está cerrado"):
            call_command("estados_financieros", NOMBRE, stdout=StringIO())
        self.assertTrue(self.eventos(Accion.EMISION_ESTADOS).filter(
            resultado=Resultado.RECHAZADO).exists())

    def test_cierre_correcto_cambia_estado_emite_y_audita(self):
        self.cerrar_como_contador()

        self.assertEqual(self.periodo.estado,
                         EstadoPeriodo.CIERRE_PROVISIONAL)
        self.assertEqual(EstadoFinancieroEmitido.objects.count(), 2)
        registro = self.eventos(Accion.CIERRE_PERIODO).get()
        self.assertEqual(registro.resultado, Resultado.EXITOSO)
        self.assertEqual(registro.actor, self.contador)
        self.assertEqual(registro.referencia, f"Período {NOMBRE}")
        self.assertEqual(registro.detalle, "Motivo: Cierre de noviembre")

    def test_cierre_rechazado_no_cambia_nada(self):
        self.client.force_login(self.contador)
        casos = [{"confirmacion": "Ejercicio"}, {"motivo": "  "}]
        for datos in casos:
            with self.subTest(datos=datos):
                respuesta = self.cerrar(**datos)
                self.assertEqual(respuesta.status_code, 400)
        self.movimiento("1101", "10")
        respuesta = self.cerrar()
        self.assertContains(respuesta, "no cuadra", status_code=400)

        self.periodo.refresh_from_db()
        self.assertFalse(self.periodo.cerrado)
        self.assertFalse(EstadoFinancieroEmitido.objects.exists())
        self.assertEqual(self.eventos(Accion.CIERRE_PERIODO).filter(
            resultado=Resultado.RECHAZADO).count(), 3)

    def test_cierre_es_atomico(self):
        self.client.force_login(self.contador)

        with patch.object(EstadosFinancierosRepository, "cerrar",
                          side_effect=GuardadoCierreError()):
            respuesta = self.cerrar()

        self.assertEqual(respuesta.status_code, 400)
        self.periodo.refresh_from_db()
        self.assertFalse(self.periodo.cerrado)
        self.assertFalse(EstadoFinancieroEmitido.objects.exists())
        self.assertFalse(self.eventos(Accion.CIERRE_PERIODO).exists())

    def test_administrador_no_cierra(self):
        self.client.force_login(self.admin)

        self.assertEqual(self.cerrar().status_code, 403)

    def test_reapertura_por_no_administrador_se_rechaza(self):
        self.cerrar_como_contador()

        respuesta = self.reabrir()

        self.assertEqual(respuesta.status_code, 403)
        self.periodo.refresh_from_db()
        self.assertTrue(self.periodo.cerrado)
        self.assertEqual(self.eventos(Accion.REAPERTURA_PERIODO).get()
                         .resultado, Resultado.RECHAZADO)

    def test_reapertura_con_contrasena_incorrecta(self):
        self.cerrar_como_contador()
        self.client.force_login(self.admin)
        intento = "otra-" + CLAVE

        respuesta = self.reabrir(contrasena=intento)

        self.assertContains(respuesta, "La contraseña no es correcta",
                            status_code=400)
        self.assertNotContains(respuesta, intento, status_code=400)
        self.periodo.refresh_from_db()
        self.assertTrue(self.periodo.cerrado)
        registro = self.eventos(Accion.REAPERTURA_PERIODO).get()
        self.assertEqual(registro.resultado,
                         Resultado.CREDENCIALES_INCORRECTAS)
        self.assertNotIn(intento, registro.detalle)

    def test_reapertura_correcta(self):
        self.cerrar_como_contador()
        self.client.force_login(self.admin)

        self.assertRedirects(self.reabrir(), reverse("cierre_periodos"))

        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, EstadoPeriodo.ABIERTO)
        registro = self.eventos(Accion.REAPERTURA_PERIODO).get()
        self.assertEqual(registro.resultado, Resultado.EXITOSO)
        self.assertEqual(registro.detalle, "Motivo: Ajuste tardío")
        self.movimiento("1101", "10")

    def test_pdf_periodo_abierto(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(reverse(
            "estado_pdf", args=[self.periodo.pk, "balance-general"]
        ))

        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn('filename="balance_general_20261231.pdf"',
                      respuesta["Content-Disposition"])
        self.assertTrue(respuesta.content.startswith(b"%PDF"))
        self.assertTrue(self.eventos(Accion.DESCARGA_ESTADO_PDF).exists())

    def test_pdf_periodo_cerrado_usa_el_snapshot(self):
        self.cerrar_como_contador()

        with patch.object(EstadosFinancierosRepository, "saldos",
                          side_effect=AssertionError("recalculó")):
            respuesta = self.client.get(reverse(
                "estado_pdf", args=[self.periodo.pk, "estado-resultados"]
            ))

        self.assertTrue(respuesta.content.startswith(b"%PDF"))
        self.assertIn("snapshot", self.eventos(
            Accion.DESCARGA_ESTADO_PDF).get().detalle)

    def test_pdf_sin_acceso(self):
        url = reverse("estado_pdf", args=[self.periodo.pk, "balance-general"])

        self.assertRedirects(self.client.get(url),
                             f"{reverse('login')}?next={url}")
        self.client.force_login(
            self.usuario("ina", Rol.CONTADOR_GENERAL, activo=False)
        )
        self.assertNotEqual(self.client.get(url).status_code, 200)
        self.assertFalse(self.eventos(Accion.DESCARGA_ESTADO_PDF).exists())
