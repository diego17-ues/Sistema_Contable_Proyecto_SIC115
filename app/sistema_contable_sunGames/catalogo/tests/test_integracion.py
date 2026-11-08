import secrets
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from bitacora.eventos import Accion
from bitacora.models import RegistroBitacora
from catalogo.models import AprobacionCuenta, Cuenta, HistorialCuenta, Subtipo
from usuarios.models import Usuario
from usuarios.roles import Rol

CLAVE = secrets.token_urlsafe(12)


class CatalogoInicialTests(TestCase):
    def test_migracion_carga_el_catalogo(self):
        self.assertEqual(Cuenta.objects.count(), 64)
        self.assertEqual(Subtipo.objects.count(), 13)
        caja = Cuenta.objects.get(codigo="1101")
        self.assertEqual(caja.denominacion, "Caja general")
        self.assertEqual(str(caja.subtipo), "11 Activo corriente")
        self.assertEqual(caja.naturaleza.nombre, "Deudora")
        self.assertEqual(
            Cuenta.objects.get(codigo="1203").naturaleza.nombre, "Acreedora"
        )
        self.assertEqual(
            Cuenta.objects.get(codigo="5103").naturaleza.nombre, "Deudora"
        )
        self.assertEqual(
            str(Cuenta.objects.get(codigo="3101").subtipo), "31 Patrimonio"
        )


class CatalogoIntegracionTests(TestCase):
    def setUp(self):
        self.admin = self.crear_usuario("admin", Rol.ADMINISTRADOR)
        self.contador = self.crear_usuario("cont", Rol.CONTADOR_GENERAL)

    def crear_usuario(self, username, rol):
        usuario = Usuario(username=username, nombre_completo="Ana", rol=rol)
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def datos(self, denominacion="Caja de eventos", rubro="1", subtipo="11",
              naturaleza="D", **extra):
        return {
            "denominacion": denominacion, "rubro": rubro, "subtipo": subtipo,
            "naturaleza": naturaleza, "referencia_respaldo": "SOL-2026-014",
            "acuerdo_numero": "JD-07/2026", "acuerdo_fecha": "2026-11-03",
            **extra,
        }

    def test_administrador_registra_con_codigo_asignado(self):
        Cuenta.objects.filter(codigo="1112").update(activa=False)
        self.client.force_login(self.admin)

        self.assertContains(
            self.client.get(reverse("cuenta_nueva")), "Código asignado"
        )
        respuesta = self.client.post(
            reverse("cuenta_nueva"), self.datos(codigo="1199")
        )

        self.assertRedirects(respuesta, reverse("accounts"))
        cuenta = Cuenta.objects.get(denominacion="Caja de eventos")
        self.assertEqual(cuenta.codigo, "1113")
        self.assertEqual(cuenta.naturaleza.nombre, "Deudora")
        self.assertFalse(Cuenta.objects.filter(codigo="1199").exists())
        aprobacion = AprobacionCuenta.objects.get(cuenta=cuenta)
        self.assertEqual(aprobacion.tipo, AprobacionCuenta.Tipo.ALTA)
        self.assertEqual(aprobacion.acuerdo_numero, "JD-07/2026")
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.ALTA_CUENTA)
        self.assertEqual(registro.actor, self.admin)
        self.assertEqual(registro.referencia, "Cuenta 1113")

    def test_vista_previa_del_codigo(self):
        self.client.force_login(self.admin)
        url = reverse("cuenta_siguiente_codigo")

        respuesta = self.client.get(url, {"rubro": "4", "subtipo": "45"})
        invalida = self.client.get(url, {"rubro": "4", "subtipo": "11"})

        self.assertEqual(respuesta.json(), {"codigo": "4504"})
        self.assertEqual(invalida.status_code, 400)
        self.assertIn("subtipo", invalida.json()["error"])

    def test_subtipo_de_otro_tipo_se_rechaza(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("cuenta_nueva"), self.datos(rubro="2", subtipo="11")
        )

        self.assertContains(
            respuesta, "El subtipo no pertenece al tipo de cuenta"
        )
        self.assertEqual(Cuenta.objects.count(), 64)

    def test_alta_sin_acuerdo_señala_el_campo(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("cuenta_nueva"), self.datos(acuerdo_numero="")
        )

        self.assertContains(respuesta, "Este campo es obligatorio.")
        self.assertContains(respuesta, 'value="Caja de eventos"')
        self.assertEqual(Cuenta.objects.count(), 64)

    def test_alta_duplicada_se_bloquea(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("cuenta_nueva"), self.datos("CAJA  GENERÁL")
        )

        self.assertContains(respuesta, "Ya existe una cuenta")
        self.assertEqual(Cuenta.objects.count(), 64)

    def test_administrador_modifica_con_revision_previa(self):
        self.client.force_login(self.admin)
        url = reverse("cuenta_modificar", args=["1101"])
        propuesta = self.datos(
            "Caja central", rubro="2", subtipo="21", codigo="2199"
        )

        self.assertContains(self.client.get(url), 'value="Caja general"')
        revision = self.client.post(url, propuesta)
        self.assertContains(revision, "Revisar cambios")
        self.assertContains(revision, "conserva su código original 1101")
        cuenta = Cuenta.objects.get(codigo="1101")
        self.assertEqual(cuenta.denominacion, "Caja general")
        self.assertFalse(HistorialCuenta.objects.exists())

        respuesta = self.client.post(
            url, {**propuesta, "confirmar": "1"}, follow=True
        )

        self.assertContains(
            respuesta, "La cuenta conserva su código original 1101."
        )
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.denominacion, "Caja central")
        self.assertEqual(str(cuenta.subtipo), "21 Pasivo corriente")
        self.assertFalse(Cuenta.objects.filter(codigo="2199").exists())
        cambio = HistorialCuenta.objects.get(campo="denominacion")
        self.assertEqual(cambio.valor_anterior, "Caja general")
        self.assertEqual(cambio.valor_nuevo, "Caja central")
        self.assertEqual(cambio.aprobacion.usuario, self.admin)
        self.assertIsNotNone(cambio.aprobacion.fecha)
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.MODIFICACION_CUENTA)
        self.assertEqual(registro.referencia, "Cuenta 1101")

    def test_falla_al_guardar_conserva_los_valores(self):
        self.client.force_login(self.admin)

        with patch(
            "catalogo.repositories.HistorialCuenta.objects.bulk_create",
            side_effect=DatabaseError,
        ):
            respuesta = self.client.post(
                reverse("cuenta_modificar", args=["1101"]),
                {**self.datos("Caja central"), "confirmar": "1"},
            )

        self.assertContains(respuesta, "conserva sus valores anteriores")
        cuenta = Cuenta.objects.get(codigo="1101")
        self.assertEqual(cuenta.denominacion, "Caja general")
        self.assertFalse(AprobacionCuenta.objects.exists())
        self.assertFalse(
            RegistroBitacora.objects.filter(
                accion=Accion.MODIFICACION_CUENTA
            ).exists()
        )

    def test_contador_consulta_sin_opciones_de_cambio(self):
        self.client.force_login(self.contador)

        listado = self.client.get(reverse("accounts"))
        detalle = self.client.get(reverse("cuenta_detalle", args=["1101"]))

        self.assertContains(listado, "Caja general")
        self.assertContains(listado, "1. ACTIVO")
        self.assertContains(listado, "11 · Activo corriente")
        self.assertContains(listado, "3. PATRIMONIO")
        self.assertNotContains(listado, "31 · Patrimonio")
        self.assertNotContains(listado, reverse("cuenta_nueva"))
        self.assertNotContains(
            listado, reverse("cuenta_modificar", args=["1101"])
        )
        self.assertContains(detalle, "Consultar cuenta")
        self.assertContains(detalle, "11 Activo corriente")

    def test_contador_recibe_403_al_registrar_o_modificar(self):
        self.client.force_login(self.contador)
        modificar = reverse("cuenta_modificar", args=["1101"])
        peticiones = [
            ("get", reverse("cuenta_nueva"), {}),
            ("post", reverse("cuenta_nueva"), self.datos()),
            ("get", reverse("cuenta_siguiente_codigo"),
             {"rubro": "1", "subtipo": "11"}),
            ("get", modificar, {}),
            ("post", modificar, self.datos("Otra")),
            ("post", modificar, {**self.datos("Otra"), "confirmar": "1"}),
        ]

        for metodo, url, datos in peticiones:
            with self.subTest(metodo=metodo, url=url):
                respuesta = getattr(self.client, metodo)(url, datos)
                self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(
            Cuenta.objects.get(codigo="1101").denominacion, "Caja general"
        )
        self.assertEqual(Cuenta.objects.count(), 64)
        self.assertFalse(AprobacionCuenta.objects.exists())

    def test_filtros_y_sin_coincidencias(self):
        Cuenta.objects.filter(codigo="1102").update(activa=False)
        self.client.force_login(self.contador)

        inactivas = self.client.get(
            reverse("accounts"), {"estado": "inactiva"}
        )
        acreedoras = self.client.get(
            reverse("accounts"), {"rubro": "1", "naturaleza": "A"}
        )
        sin_resultados = self.client.get(
            reverse("accounts"), {"denominacion": "zzz"}
        )
        invalido = self.client.get(reverse("accounts"), {"codigo": "11a"})

        self.assertContains(inactivas, "Caja chica")
        self.assertNotContains(inactivas, "Caja general")
        self.assertContains(acreedoras, "Depreciación acumulada")
        self.assertNotContains(acreedoras, "Caja general")
        self.assertContains(
            sin_resultados, "No hay cuentas para los criterios indicados."
        )
        self.assertContains(invalido, "El código admite solo dígitos")
        self.assertNotContains(invalido, "Caja general")

    def test_formulario_de_alta_no_tiene_campo_de_codigo(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(reverse("cuenta_nueva"))

        html = respuesta.content.decode()
        inicio = html.index(f'action="{reverse("cuenta_nueva")}"')
        formulario = html[inicio:]
        self.assertNotIn('name="codigo"', formulario)
        self.assertIn('name="subtipo"', formulario)
        self.assertNotIn('name="justificacion"', formulario)
        self.assertEqual(html.count('id="id_rubro"'), 1)
        self.assertEqual(html.count('id="filtro_rubro"'), 1)
        self.assertNotIn('name="descripcion"', formulario)
