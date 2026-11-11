import json
import secrets
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from bitacora.eventos import Accion, Resultado
from bitacora.models import RegistroBitacora
from catalogo.tests.fakes import BitacoraEnMemoria
from estados_financieros.models import EstadoFinancieroEmitido
from libro_mayor.models import (
    EstadoPeriodo,
    Movimiento,
    PeriodoContable,
    Transaccion,
)
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
        self.ventas, self.contacto, self.error = {}, None, None

    def existe(self, identificador):
        return identificador in self.ventas

    def crear(self, **datos):
        venta = Venta(**datos)
        self.ventas[venta.identificador] = venta
        return venta

    def registrar_contacto(self, momento):
        self.contacto = momento
        self.error = None

    def registrar_error(self, momento):
        self.error = momento

    def ultimo_contacto(self):
        return self.contacto

    def ultimo_error(self):
        return self.error

    def ventas_en_periodo(self, desde, hasta):
        return [venta for venta in self.ventas.values()
                if desde <= venta.fecha <= hasta]

    def marcar_registrada(self, venta, transaccion):
        venta.estado = EstadoVenta.REGISTRADA
        venta.transaccion_id = transaccion.pk
        return venta

    def obtener(self, identificador):
        return self.ventas[identificador]


class MayorEnMemoria:
    def __init__(self):
        self.movimientos = []
        self.transacciones = 0

    def periodo_de(self, fecha):
        return SimpleNamespace(cerrado=False)

    def obtener_cuenta(self, codigo):
        return SimpleNamespace(codigo=codigo, activa=True)

    def tiene_subcuentas(self, cuenta):
        return False

    def crear_transaccion(self, usuario):
        self.transacciones += 1
        return SimpleNamespace(pk=self.transacciones)

    def crear_movimiento(self, **datos):
        self.movimientos.append(datos)


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

    def test_recibe_evento_no_actualiza_el_estado_del_latido(self):
        venta = self.recibir()

        self.assertEqual(venta.estado, EstadoVenta.PENDIENTE)
        self.assertEqual(venta.total, Decimal("39.98"))
        self.assertEqual(venta.neto, Decimal("27.98"))
        self.assertEqual(self.servicio.estado_conexion().estado, "En espera")

        self.servicio.latido()
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

    def test_error_autenticado_se_muestra_hasta_el_siguiente_latido(self):
        self.servicio.registrar_error()
        self.assertEqual(self.servicio.estado_conexion().estado, "Error")

        self.servicio.latido()

        self.assertEqual(self.servicio.estado_conexion().estado, "Conectado")

    def test_conciliacion_contabiliza_una_vez_por_evento(self):
        venta = self.recibir()
        mayor = MayorEnMemoria()
        servicio = VentasService(self.repo, mayor, self.bitacora,
                                 reloj=lambda: AHORA)
        actor = crear_usuario("contador", Rol.CONTADOR_GENERAL)
        desde, hasta = date(2026, 11, 1), date(2026, 11, 30)

        primero = servicio.conciliar(actor, desde, hasta)
        segundo = servicio.conciliar(actor, desde, hasta)

        self.assertEqual(primero.conciliadas, 1)
        self.assertEqual(primero.total, Decimal("39.98"))
        self.assertEqual(primero.cuentas_por_cobrar, Decimal("27.98"))
        self.assertEqual(primero.comision, Decimal("12.00"))
        self.assertEqual(segundo.conciliadas, 1)
        self.assertEqual(len(mayor.movimientos), 3)
        self.assertEqual(mayor.transacciones, 1)
        self.assertEqual(venta.estado, EstadoVenta.REGISTRADA)

    def test_conciliacion_repite_evento_sin_duplicar_asiento(self):
        venta = self.recibir()
        mayor = MayorEnMemoria()
        servicio = VentasService(self.repo, mayor, self.bitacora,
                                 reloj=lambda: AHORA)
        actor = crear_usuario("contador", Rol.CONTADOR_GENERAL)
        desde, hasta = date(2026, 11, 1), date(2026, 11, 30)

        primera = servicio.conciliar(actor, desde, hasta)
        segunda = servicio.conciliar(actor, desde, hasta)

        self.assertEqual(segunda.conciliadas, 1)
        self.assertEqual(segunda.total, primera.total)
        self.assertEqual(len(mayor.movimientos), 3)
        self.assertEqual(mayor.transacciones, 1)
        self.assertEqual(venta.estado, EstadoVenta.REGISTRADA)

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

    def conciliar(self, method="post", **datos):
        return getattr(self.client, method)(
            reverse("api_conciliar_ventas"), datos
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

    def test_error_autenticado_actualiza_estado_hasta_latido(self):
        self.assertEqual(
            self.enviar(evento(cantidad=0)).status_code, 422
        )
        self.client.force_login(self.contador)

        conexion = self.client.get(reverse("api_ventas")).json()["conexion"]
        self.assertEqual(conexion["estado"], "Error")
        self.assertIsNotNone(conexion["ultimoError"])

        self.client.logout()
        latido = self.client.post(
            reverse("steam_latido"), HTTP_AUTHORIZATION=f"Bearer {TOKEN}"
        )
        self.assertEqual(latido.status_code, 200)
        self.client.force_login(self.contador)
        conexion = self.client.get(reverse("api_ventas")).json()["conexion"]
        self.assertEqual(conexion["estado"], "Conectado")
        self.assertIsNone(conexion["ultimoError"])

    @override_settings(STEAM_WEBHOOK_TOKEN="")
    def test_webhook_sin_token_configurado(self):
        self.assertEqual(self.enviar(evento()).status_code, 503)

    def test_contador_contabiliza_con_asiento_balanceado(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        self.client.post(
            reverse("steam_latido"), HTTP_AUTHORIZATION=f"Bearer {TOKEN}"
        )

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

    def test_conciliar_una_vez_por_evento_y_auditar(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        rango = {"desde": "2026-11-01", "hasta": "2026-11-30"}

        vista_previa = self.conciliar("get", **rango)
        primera = self.conciliar(**rango)
        segunda = self.conciliar(**rango)

        self.assertEqual(vista_previa.status_code, 200)
        self.assertEqual(vista_previa.json()["cuentasPorCobrar"], "27.98")
        self.assertEqual(vista_previa.json()["comision"], "12.00")
        self.assertEqual(primera.status_code, 200, primera.content)
        self.assertEqual(primera.json()["conciliadas"], 1)
        self.assertEqual(primera.json()["total"], "39.98")
        self.assertEqual(segunda.status_code, 200, segunda.content)
        self.assertEqual(segunda.json()["conciliadas"], 1)
        self.assertEqual(Movimiento.objects.count(), 3)
        self.assertEqual(Transaccion.objects.count(), 1)
        self.assertEqual(RegistroBitacora.objects.filter(
            accion=Accion.CONCILIACION_VENTAS
        ).count(), 2)

    def test_conciliar_permite_evento_contabilizado_en_periodo_cerrado(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        self.assertEqual(self.contabilizar().status_code, 200)
        periodo = PeriodoContable.objects.get(nombre="Ejercicio 2026")
        periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL
        periodo.save()

        vista_previa = self.conciliar(
            "get", desde="2026-11-01", hasta="2026-11-30"
        )
        movimientos_antes = Movimiento.objects.count()
        respuesta = self.conciliar(
            desde="2026-11-01", hasta="2026-11-30"
        )
        segunda = self.conciliar(
            desde="2026-11-01", hasta="2026-11-30"
        )

        self.assertEqual(vista_previa.status_code, 200)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()["conciliadas"], 1)
        self.assertEqual(segunda.status_code, 200, segunda.content)
        self.assertEqual(segunda.json()["conciliadas"], 1)
        self.assertEqual(Movimiento.objects.count(), movimientos_antes)
        self.assertEqual(Transaccion.objects.count(), 1)
        self.assertEqual(Venta.objects.get().estado, EstadoVenta.REGISTRADA)
        self.assertEqual(RegistroBitacora.objects.filter(
            accion=Accion.CONCILIACION_VENTAS
        ).count(), 2)

    def test_conciliar_no_contabiliza_evento_pendiente_en_periodo_cerrado(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        periodo = PeriodoContable.objects.get(nombre="Ejercicio 2026")
        periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL
        periodo.save()

        vista_previa = self.conciliar(
            "get", desde="2026-11-01", hasta="2026-11-30"
        )
        respuesta = self.conciliar(
            desde="2026-11-01", hasta="2026-11-30"
        )

        self.assertEqual(vista_previa.status_code, 200)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()["conciliadas"], 0)
        self.assertEqual(len(respuesta.json()["errores"]), 1)
        self.assertFalse(Movimiento.objects.exists())
        self.assertEqual(Venta.objects.get().estado, EstadoVenta.PENDIENTE)
        self.assertEqual(RegistroBitacora.objects.get(
            accion=Accion.CONCILIACION_VENTAS
        ).resultado, Resultado.RECHAZADO)

    def test_cierre_se_bloquea_con_ventas_pendientes(self):
        self.enviar(evento())
        self.client.force_login(self.contador)
        datos = {"desde": "2026-11-01", "hasta": "2026-11-30",
                 "confirmacion": "CONFIRMAR", "motivo": "Cierre"}

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


class EstadoConexionUiTests(SimpleTestCase):
    def test_panel_de_estado_de_conexion_no_tiene_controles_editables(self):
        ruta = finders.find("sic_sunGames/app.js")
        fuente = Path(ruta).read_text(encoding="utf-8")
        panel = fuente.split("function steamPanel()", 1)[1].split(
            "function showToast(", 1
        )[0]

        self.assertNotRegex(panel, r"<(input|select|textarea)\b")
        self.assertNotIn("data-action=\"steam-check\"", panel)
        self.assertIn("Solo lectura", panel)
