import secrets
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from bitacora.eventos import Accion
from bitacora.models import RegistroBitacora
from libro_mayor.models import Movimiento, Transaccion
from usuarios.models import Usuario
from usuarios.roles import Rol

CLAVE = secrets.token_urlsafe(12)


def datos_post(lineas, fecha="2026-11-03", concepto="Venta del día"):
    datos = {
        "fecha": fecha, "concepto": concepto,
        "mov-TOTAL_FORMS": str(len(lineas)), "mov-INITIAL_FORMS": "0",
        "mov-MIN_NUM_FORMS": "0", "mov-MAX_NUM_FORMS": "1000",
    }
    for indice, (cuenta, importe) in enumerate(lineas):
        datos[f"mov-{indice}-cuenta"] = cuenta
        datos[f"mov-{indice}-importe"] = importe
    return datos


class LibroMayorIntegracionTests(TestCase):
    def setUp(self):
        self.contador = self.crear_usuario("cont", Rol.CONTADOR_GENERAL)
        self.admin = self.crear_usuario("admin", Rol.ADMINISTRADOR)

    def crear_usuario(self, username, rol):
        usuario = Usuario(username=username, nombre_completo="Ana", rol=rol)
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def test_contador_registra_y_ve_saldos_actualizados(self):
        self.client.force_login(self.contador)
        lineas = [("1101", "113.00"), ("5101", "-100.00"),
                  ("2103", "-13.00"), ("", "")]

        respuesta = self.client.post(
            reverse("transaccion_registrar"), datos_post(lineas)
        )

        self.assertRedirects(respuesta, reverse("ledger"))
        transaccion = Transaccion.objects.get()
        self.assertEqual(transaccion.movimientos.count(), 3)
        self.assertEqual(transaccion.usuario, self.contador)
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.REGISTRO_TRANSACCION)
        saldo = self.client.get(reverse("ledger"), {
            "saldo-cuenta": "5101", "saldo-fecha_corte": "2026-11-30"
        })
        self.assertContains(saldo, "100.00")
        self.assertContains(saldo, "Saldo acreedor")
        consulta = self.client.get(reverse("ledger"), {
            "consulta-cuenta": "1101", "consulta-desde": "2026-11-01",
            "consulta-hasta": "2026-11-30",
        })
        self.assertContains(consulta, "Venta del día")
        self.assertContains(consulta, "113.00")

    def test_descuadrada_muestra_la_diferencia_y_no_guarda(self):
        self.client.force_login(self.contador)

        respuesta = self.client.post(
            reverse("transaccion_registrar"),
            datos_post([("1101", "100"), ("5101", "-90")]),
        )

        self.assertContains(respuesta, "la suma de los importes es 10.00")
        self.assertContains(respuesta, 'value="Venta del día"')
        self.assertFalse(Transaccion.objects.exists())

    def test_cuenta_repetida_senala_las_lineas(self):
        self.client.force_login(self.contador)

        respuesta = self.client.post(
            reverse("transaccion_registrar"),
            datos_post([("1101", "10"), ("5101", "-20"), ("1101", "10")]),
        )

        self.assertContains(
            respuesta, "La cuenta aparece más de una vez", count=2
        )
        self.assertFalse(Movimiento.objects.exists())

    def test_falla_del_ultimo_movimiento_no_deja_nada(self):
        self.client.force_login(self.contador)
        guardar = Movimiento.save
        llamadas = []

        def fallar_en_el_tercero(movimiento, *args, **kwargs):
            llamadas.append(movimiento)
            if len(llamadas) == 3:
                raise DatabaseError("falla simulada")
            return guardar(movimiento, *args, **kwargs)

        with patch.object(Movimiento, "save", fallar_en_el_tercero):
            respuesta = self.client.post(
                reverse("transaccion_registrar"),
                datos_post([("1101", "113"), ("5101", "-100"),
                            ("2103", "-13")]),
            )

        self.assertContains(respuesta, "no se registró ningún cambio")
        self.assertFalse(Transaccion.objects.exists())
        self.assertFalse(Movimiento.objects.exists())
        self.assertFalse(RegistroBitacora.objects.filter(
            accion=Accion.REGISTRO_TRANSACCION).exists())

    def test_otro_rol_recibe_403_al_registrar(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("transaccion_registrar"),
            datos_post([("1101", "5"), ("5101", "-5")]),
        )
        pantalla = self.client.get(reverse("ledger"))

        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Transaccion.objects.exists())
        self.assertNotContains(pantalla, reverse("transaccion_registrar"))
