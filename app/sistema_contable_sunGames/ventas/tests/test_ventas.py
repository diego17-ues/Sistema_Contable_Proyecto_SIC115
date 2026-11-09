import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from bitacora.eventos import Accion, Resultado
from bitacora.models import RegistroBitacora
from catalogo.tests.fakes import BitacoraEnMemoria
from estados_financieros.models import EstadoFinancieroEmitido
from libro_mayor.models import EstadoPeriodo, Movimiento, PeriodoContable
from simulador_steam.simulador import generar_evento
from usuarios.exceptions import RolNoAutorizadoError
from usuarios.models import Usuario
from usuarios.roles import Rol
from usuarios.tests.fakes import crear_usuario
from ventas.exceptions import (
    EventoInvalidoError,
    MonedaNoAdmitidaError,
    VentaDuplicadaError,
)
from ventas.models import EstadoVenta, Venta
from ventas.services import VentasService

TOKEN = secrets.token_urlsafe(16)
CLAVE = secrets.token_urlsafe(12)
AHORA = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)


def evento(**cambios):
    datos = {
        "id": "STM-0001", "titulo": "Título A", "tipo": "JUEGO",
        "cantidad": 2, "precio_unitario": "19.99", "moneda": "USD",
        "pais": "SV", "fecha_hora": AHORA.isoformat(), "comision": "12.00",
        "impuesto": "0.00",
    }
    datos.update(cambios)
    return datos


class RepoEnMemoria:
    def __init__(self):
        self.ventas, self.contacto = {}, None

    def existe(self, identificador):
        return identificador in self.ventas

    def crear(self, **datos):
        venta = Venta(**datos)
        self.ventas[venta.identificador] = venta
        return venta

    def registrar_contacto(self, momento):
        self.contacto = momento

    def ultimo_contacto(self):
        return self.contacto


class VentasServiceTests(SimpleTestCase):
    def setUp(self):
        self.repo = RepoEnMemoria()
        self.bitacora = BitacoraEnMemoria()
        self.servicio = VentasService(self.repo, None, self.bitacora,
                                      reloj=lambda: AHORA)

    def recibir(self, **cambios):
        datos = evento(**cambios)
        return self.servicio.recibir(
            identificador=datos["id"], titulo=datos["titulo"],
            tipo_producto=datos["tipo"], cantidad=datos["cantidad"],
            precio_unitario=Decimal(datos["precio_unitario"]),
            moneda=datos["moneda"], pais=datos["pais"], fecha_hora=AHORA,
            comision=Decimal(datos["comision"]),
        )

    def test_recibe_evento_valido_pendiente_y_conectado(self):
        venta = self.recibir()

        self.assertEqual(venta.estado, EstadoVenta.PENDIENTE)
        self.assertEqual(venta.total, Decimal("39.98"))
        self.assertEqual(venta.neto, Decimal("27.98"))
        self.assertEqual(self.servicio.estado_conexion().estado, "Conectado")

    def test_rechaza_duplicado_moneda_y_comision_excesiva(self):
        self.recibir()
        for cambios, error in (({}, VentaDuplicadaError),
                               ({"id": "STM-2", "moneda": "EUR"},
                                MonedaNoAdmitidaError),
                               ({"id": "STM-3", "comision": "50"},
                                EventoInvalidoError)):
            with self.subTest(cambios=cambios), self.assertRaises(error):
                self.recibir(**cambios)
        resultados = [r["resultado"] for r in self.bitacora.registros]
        self.assertEqual(resultados.count(Resultado.RECHAZADO), 3)

    def test_sin_contacto_queda_en_espera(self):
        self.assertEqual(self.servicio.estado_conexion().estado, "En espera")

    def test_solo_el_contador_general_contabiliza(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.contabilizar(crear_usuario(), "STM-0001")

    def test_el_simulador_genera_eventos_validos(self):
        from ventas.forms import EventoSteamForm

        form = EventoSteamForm(generar_evento())

        self.assertTrue(form.is_valid(), form.errors)


@override_settings(STEAM_WEBHOOK_TOKEN=TOKEN)
class VentasIntegracionTests(TestCase):
    def setUp(self):
        self.contador = self.usuario("cont", Rol.CONTADOR_GENERAL)
        self.admin = self.usuario("admin", Rol.ADMINISTRADOR)

    def usuario(self, username, rol):
        usuario = Usuario(username=username, nombre_completo="Ana", rol=rol)
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def enviar(self, datos, token=TOKEN):
        return self.client.post(
            reverse("steam_ventas"), json.dumps(datos),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def contabilizar(self, identificador="STM-0001"):
        return self.client.post(
            reverse("api_contabilizar_venta", args=[identificador])
        )

    def test_webhook_valida_token_formato_y_duplicados(self):
        self.assertEqual(self.enviar(evento(), token="otro").status_code, 401)
        self.assertEqual(self.enviar(evento()).status_code, 201)
        self.assertEqual(self.enviar(evento()).status_code, 409)
        self.assertEqual(
            self.enviar(evento(id="STM-2", moneda="EUR")).status_code, 422
        )
        self.assertEqual(
            self.enviar(evento(id="STM-3", cantidad=0)).status_code, 422
        )
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(RegistroBitacora.objects.filter(
            accion=Accion.RECEPCION_VENTA, resultado=Resultado.RECHAZADO
        ).count(), 3)

    @override_settings(STEAM_WEBHOOK_TOKEN="")
    def test_webhook_sin_token_configurado(self):
        self.assertEqual(self.enviar(evento()).status_code, 503)

    def test_contador_contabiliza_con_asiento_balanceado(self):
        self.enviar(evento())
        self.client.force_login(self.contador)

        listado = self.client.get(reverse("api_ventas")).json()
        respuesta = self.contabilizar()

        self.assertEqual(listado["ventas"][0]["status"], "Pendiente")
        self.assertEqual(listado["conexion"]["estado"], "Conectado")
        self.assertEqual(respuesta.status_code, 200)
        importes = dict(Movimiento.objects.values_list("cuenta__codigo",
                                                       "importe"))
        self.assertEqual(importes, {"1104": Decimal("27.98"),
                                    "4302": Decimal("12.00"),
                                    "5101": Decimal("-39.98")})
        self.assertEqual(Venta.objects.get().estado, EstadoVenta.REGISTRADA)
        self.assertEqual(self.contabilizar().status_code, 422)
        self.assertEqual(Movimiento.objects.count(), 3)
        self.assertTrue(RegistroBitacora.objects.filter(
            accion=Accion.CONTABILIZACION_VENTA).exists())

    def test_dlc_va_a_5102_y_administrador_no_contabiliza(self):
        self.enviar(evento(tipo="DLC"))
        self.client.force_login(self.admin)
        self.assertEqual(self.contabilizar().status_code, 403)

        self.client.force_login(self.contador)
        self.contabilizar()
        self.assertTrue(Movimiento.objects.filter(cuenta__codigo="5102")
                        .exists())

    def test_cierre_se_bloquea_con_ventas_pendientes(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        datos = {"desde": "2026-11-01", "hasta": "2026-11-30",
                 "confirmacion": "Provisional 2026-11", "motivo": "Cierre"}

        hoja = self.client.get(reverse("api_hoja_trabajo"), datos).json()
        bloqueado = self.client.post(reverse("api_cierre_provisional"), datos)
        self.contabilizar()
        cerrado = self.client.post(reverse("api_cierre_provisional"), datos)

        self.assertEqual(hoja["ventasPendientes"], 1)
        self.assertEqual(hoja["periodo"]["nombre"], "Provisional 2026-11")
        self.assertEqual(bloqueado.status_code, 422)
        self.assertIn("venta(s) pendientes", bloqueado.json()["error"])
        self.assertEqual(cerrado.status_code, 200, cerrado.content)
        periodo = PeriodoContable.objects.get(nombre="Provisional 2026-11")
        self.assertEqual(periodo.estado, EstadoPeriodo.CIERRE_PROVISIONAL)
        self.assertEqual(
            EstadoFinancieroEmitido.objects.filter(periodo=periodo).count(), 2
        )
        self.enviar(evento(id="STM-9"))
        self.assertEqual(self.contabilizar("STM-9").status_code, 422)

    def test_hoja_de_trabajo_y_ajuste_desde_la_api(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        self.contabilizar()
        rango = {"desde": "2026-11-01", "hasta": "2026-11-30"}

        ajuste = self.client.post(reverse("api_ajuste"), {
            "code": "1104", "date": "2026-11-30", "concept": "Ajuste",
            "debit": "", "credit": "2.00",
        })
        hoja = self.client.get(reverse("api_hoja_trabajo"), rango).json()

        self.assertEqual(ajuste.status_code, 200, ajuste.content)
        filas = {f["code"]: f for f in hoja["worksheet"]["rows"]}
        self.assertEqual(filas["1104"]["trialDebit"], "27.98")
        self.assertEqual(filas["1104"]["adjustCredit"], "2.00")
        self.assertEqual(filas["1104"]["adjustedDebit"], "25.98")
        self.assertEqual(hoja["worksheet"]["adjustments"][0]["side"],
                         "Abono")
        self.assertEqual(hoja["estado"], "ABIERTO")

    def test_pdf_niif_de_un_rango(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("estado_pdf_rango", args=["balance-general"]),
            {"desde": "2026-11-01", "hasta": "2026-11-30"},
        )

        self.assertTrue(respuesta.content.startswith(b"%PDF"))

    def test_pantalla_de_ventas_sin_datos_de_ejemplo(self):
        self.client.force_login(self.contador)
        listado = self.client.get(reverse("api_ventas")).json()
        self.assertEqual(listado["ventas"], [])
        self.assertEqual(listado["conexion"]["estado"], "En espera")
