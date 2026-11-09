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


def datos_post(cuenta, lineas):
    datos = {
        "cuenta": cuenta,
        "mov-TOTAL_FORMS": str(len(lineas)), "mov-INITIAL_FORMS": "0",
        "mov-MIN_NUM_FORMS": "0", "mov-MAX_NUM_FORMS": "1000",
    }
    for indice, (fecha, concepto, tipo, debe, haber) in enumerate(lineas):
        datos.update({
            f"mov-{indice}-fecha": fecha,
            f"mov-{indice}-concepto": concepto,
            f"mov-{indice}-referencia": f"V-{indice}",
            f"mov-{indice}-tipo": tipo,
            f"mov-{indice}-debe": debe,
            f"mov-{indice}-haber": haber,
        })
    return datos


INGRESO = "COMPROBANTE_INGRESO"


class LibroMayorIntegracionTests(TestCase):
    def setUp(self):
        self.contador = self.crear_usuario("cont", Rol.CONTADOR_GENERAL)
        self.admin = self.crear_usuario("admin", Rol.ADMINISTRADOR)

    def crear_usuario(self, username, rol):
        usuario = Usuario(username=username, nombre_completo="Ana", rol=rol)
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def registrar(self, cuenta, lineas):
        return self.client.post(
            reverse("transaccion_registrar"), datos_post(cuenta, lineas)
        )

    def test_pantalla_conserva_los_campos_originales(self):
        self.client.force_login(self.contador)

        pantalla = self.client.get(reverse("ledger"))

        for texto in ("Cuenta del Libro Mayor", "Registrar transacción",
                      "<th>Ref.</th>", "<th>Tipo</th>", ">Debe</th>",
                      ">Haber</th>", "Guardar en Libro Mayor",
                      "Detalle del Libro Mayor", "Balance de comprobación",
                      'id="ledgerAccountFilter"', 'id="ledgerFrom"'):
            self.assertContains(pantalla, texto)
        self.assertNotContains(pantalla, "Importe")

    def test_contador_registra_en_debe_y_haber_y_consulta_saldos(self):
        self.client.force_login(self.contador)

        respuesta = self.registrar("1101", [
            ("2026-11-03", "Venta del día", INGRESO, "113.00", ""),
            ("2026-11-04", "Pago a proveedor", "COMPROBANTE_EGRESO", "",
             "20.00"),
        ])

        self.assertRedirects(
            respuesta, f"{reverse('ledger')}?cuenta=1101&desde=&hasta="
        )
        transaccion = Transaccion.objects.get()
        self.assertEqual(
            sorted(transaccion.movimientos.values_list("importe", flat=True)),
            [-20, 113],
        )
        self.assertEqual(transaccion.usuario, self.contador)
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.REGISTRO_TRANSACCION)
        detalle = self.client.get(reverse("ledger"), {
            "cuenta": "1101", "desde": "2026-11-01", "hasta": "2026-11-30",
        })
        self.assertContains(detalle, "Venta del día")
        self.assertContains(detalle, "Comprobante de Ingreso-2026-00001")
        self.assertContains(detalle, "$113.00")
        self.assertContains(detalle, "$93.00")
        self.assertContains(detalle, "Saldo al 30/11/2026")

    def test_no_exige_cuadre_y_el_balance_muestra_solo_cuentas_con_monto(self):
        self.client.force_login(self.contador)
        self.registrar("1101", [("2026-11-03", "Venta", INGRESO, "100", "")])
        self.registrar("5101", [("2026-11-03", "Venta", INGRESO, "", "90")])

        balance = self.client.get(reverse("ledger"), {
            "mode": "trial-balance", "corte": "2026-11-30",
        })

        self.assertEqual(Movimiento.objects.count(), 2)
        self.assertContains(balance, "1101 · Caja general")
        self.assertContains(balance, "5101 · Ingresos por licencias")
        self.assertNotContains(balance, "1102 · Caja chica")
        self.assertContains(balance, "Diferencia $10.00")

    def test_linea_invalida_se_senala_y_no_guarda_nada(self):
        self.client.force_login(self.contador)

        respuesta = self.registrar("1101", [
            ("2026-11-03", "Venta del día", INGRESO, "50", ""),
            ("2026-11-03", "Venta doble", INGRESO, "5", "5"),
        ])

        self.assertContains(
            respuesta, "Registra el monto solo en Debe o solo en Haber."
        )
        self.assertContains(respuesta, 'value="Venta del día"')
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
            respuesta = self.registrar("1101", [
                ("2026-11-03", "Uno", INGRESO, "1", ""),
                ("2026-11-03", "Dos", INGRESO, "2", ""),
                ("2026-11-03", "Tres", INGRESO, "", "3"),
            ])

        self.assertContains(respuesta, "no se registró ningún cambio")
        self.assertFalse(Transaccion.objects.exists())
        self.assertFalse(Movimiento.objects.exists())
        self.assertFalse(RegistroBitacora.objects.filter(
            accion=Accion.REGISTRO_TRANSACCION).exists())

    def test_otro_rol_recibe_403_al_registrar(self):
        self.client.force_login(self.admin)

        respuesta = self.registrar(
            "1101", [("2026-11-03", "Venta", INGRESO, "5", "")]
        )
        pantalla = self.client.get(reverse("ledger"))
        balance = self.client.get(reverse("ledger"), {"mode": "trial-balance"})

        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Movimiento.objects.exists())
        self.assertNotContains(pantalla, reverse("transaccion_registrar"))
        self.assertEqual(balance.status_code, 200)
