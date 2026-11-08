import secrets
from unittest.mock import patch

from django.contrib.auth import SESSION_KEY
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from bitacora.eventos import Accion, Resultado
from bitacora.models import RegistroBitacora
from usuarios.autenticacion import AutenticadorDjango
from usuarios.exceptions import ServicioAutenticacionError
from usuarios.models import Usuario
from usuarios.roles import Rol

from .forms import LoginForm

CLAVE = secrets.token_urlsafe(12)
CREDENCIALES_INCORRECTAS = "Nombre de usuario o contraseña incorrectos."
CUENTA_NO_HABILITADA = "La cuenta no está habilitada para iniciar sesión."
FALLA_SERVICIO = "No se pudo iniciar sesión; intente nuevamente."


class LoginFormTests(SimpleTestCase):
    def test_campos_obligatorios(self):
        form = LoginForm(data={"username": "", "password": ""})

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["username"], ["Este campo es obligatorio."]
        )
        self.assertEqual(
            form.errors["password"], ["Este campo es obligatorio."]
        )

    def test_campo_vacio_conserva_el_otro_valor(self):
        form = LoginForm(data={"username": "contador", "password": ""})

        self.assertFalse(form.is_valid())
        self.assertNotIn("username", form.errors)
        self.assertIn('value="contador"', str(form["username"]))

    def test_contrasena_oculta(self):
        self.assertIn('type="password"', str(LoginForm()["password"]))


class LoginIntegracionTests(TestCase):
    def setUp(self):
        self.url = reverse("login")
        self.contador = self.crear_usuario("contador", Rol.CONTADOR_GENERAL)

    def crear_usuario(self, username, rol, activo=True):
        usuario = Usuario(
            username=username, nombre_completo="Ana Gómez", rol=rol,
            activo=activo,
        )
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def post(self, username, password):
        return self.client.post(
            self.url, {"username": username, "password": password}
        )

    def ultimo_registro(self):
        return RegistroBitacora.objects.latest("id")

    def assert_sin_sesion(self):
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_pantalla_de_login_sin_menu_de_modulos(self):
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, 'name="username"')
        self.assertContains(respuesta, 'type="password"')
        self.assertContains(respuesta, "Iniciar sesión")
        self.assertNotContains(respuesta, 'id="appShell"')
        self.assertNotContains(respuesta, 'id="sidebar"')

    def test_modulos_requieren_sesion(self):
        respuesta = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            respuesta, f"{self.url}?next={reverse('dashboard')}"
        )

    def test_credenciales_validas_crean_sesion(self):
        respuesta = self.post("contador", CLAVE)

        self.assertRedirects(respuesta, reverse("dashboard"))
        self.assertEqual(
            self.client.session[SESSION_KEY], str(self.contador.pk)
        )
        registro = self.ultimo_registro()
        self.assertEqual(registro.accion, Accion.INICIO_SESION)
        self.assertEqual(registro.resultado, Resultado.EXITOSO)
        self.assertEqual(registro.actor, self.contador)

        panel = self.client.get(reverse("dashboard"))
        self.assertContains(panel, 'id="sidebar"')
        self.assertContains(panel, "Contador General")

    def test_credenciales_incorrectas_no_crean_sesion(self):
        for username, password in (("contador", "otra"), ("nadie", "x")):
            respuesta = self.post(username, password)

            self.assertContains(respuesta, CREDENCIALES_INCORRECTAS)
            self.assertContains(respuesta, f'value="{username}"')
            self.assertNotContains(respuesta, f'value="{password}"')
            self.assert_sin_sesion()
            self.assertEqual(
                self.ultimo_registro().resultado,
                Resultado.CREDENCIALES_INCORRECTAS,
            )

    def test_cuenta_inactiva_no_crea_sesion(self):
        inactivo = self.crear_usuario(
            "inactivo", Rol.CONTADOR_GENERAL, activo=False
        )

        respuesta = self.post("inactivo", CLAVE)

        self.assertContains(respuesta, CUENTA_NO_HABILITADA)
        self.assert_sin_sesion()
        registro = self.ultimo_registro()
        self.assertEqual(registro.resultado, Resultado.CUENTA_NO_HABILITADA)
        self.assertEqual(registro.actor, inactivo)

    def test_campo_vacio_se_senala_y_conserva_el_usuario(self):
        respuesta = self.post("contador", "")

        self.assertContains(respuesta, "Este campo es obligatorio.", count=1)
        self.assertContains(respuesta, 'value="contador"')
        self.assert_sin_sesion()
        registro = self.ultimo_registro()
        self.assertEqual(registro.resultado, Resultado.DATOS_INCOMPLETOS)
        self.assertEqual(registro.actor, self.contador)

    def test_falla_del_servicio_no_crea_sesion(self):
        with patch.object(
            AutenticadorDjango, "verificar_credenciales",
            side_effect=ServicioAutenticacionError(),
        ):
            respuesta = self.post("contador", CLAVE)

        self.assertContains(respuesta, FALLA_SERVICIO)
        self.assert_sin_sesion()
        self.assertEqual(
            self.ultimo_registro().resultado, Resultado.ERROR_SERVICIO
        )

    def test_administrador_entra_a_usuarios(self):
        self.crear_usuario("admin", Rol.ADMINISTRADOR)

        respuesta = self.post("admin", CLAVE)

        self.assertRedirects(respuesta, reverse("users"))
        self.assertIn(SESSION_KEY, self.client.session)

    def test_contador_no_accede_a_modulos_de_administrador(self):
        self.client.force_login(self.contador)

        for nombre in ("users", "audit"):
            self.assertEqual(
                self.client.get(reverse(nombre)).status_code, 403
            )

    def test_cerrar_sesion(self):
        self.client.force_login(self.contador)

        respuesta = self.client.post(reverse("logout"))

        self.assertRedirects(respuesta, self.url)
        self.assert_sin_sesion()


class AppJsSinDatosDeDemostracionTests(SimpleTestCase):
    def setUp(self):
        ruta = finders.find("sic_sunGames/app.js")
        with open(ruta, encoding="utf-8") as archivo:
            self.codigo = archivo.read()

    def test_sin_contrasena_de_sesion_en_el_cliente(self):
        self.assertNotIn("session" + "Password", self.codigo)
        self.assertNotIn("data.password", self.codigo)

    def test_sin_usuarios_fijos_ni_perfiles_inexistentes(self):
        self.assertNotIn("username:", self.codigo)
        self.assertNotIn("Auxiliar " + "Contable", self.codigo)

    def test_sin_bitacora_en_el_cliente(self):
        self.assertNotIn("addAudit", self.codigo)
        self.assertNotIn("state.audit", self.codigo)


class AdministracionIntegracionTests(TestCase):
    """CU-02 y CU-03 contra PostgreSQL."""

    def setUp(self):
        self.admin = self.crear_usuario("admin", Rol.ADMINISTRADOR)
        self.contador = self.crear_usuario("cont", Rol.CONTADOR_GENERAL)

    def crear_usuario(self, username, rol):
        usuario = Usuario(username=username, nombre_completo="Ana", rol=rol)
        usuario.set_password(CLAVE)
        usuario.save()
        return usuario

    def test_administrador_accede_a_usuarios_y_auditoria(self):
        self.client.force_login(self.admin)

        usuarios = self.client.get(reverse("users"))
        auditoria = self.client.get(reverse("audit"))

        self.assertContains(usuarios, "Usuarios del sistema")
        self.assertContains(usuarios, "cont")
        self.assertNotContains(usuarios, "Guardar cambios")
        self.assertContains(auditoria, "Registro de actividad")

    def test_administrador_accede_a_pantallas_del_contador(self):
        self.client.force_login(self.admin)

        for nombre in ("dashboard", "ledger", "accounts", "reports",
                       "operations"):
            self.assertEqual(
                self.client.get(reverse(nombre)).status_code, 200, nombre
            )

    def test_contador_recibe_403_en_usuarios_y_auditoria(self):
        self.client.force_login(self.contador)
        urls = [
            reverse("users"), reverse("audit"), reverse("usuario_nuevo"),
            reverse("usuario_detalle", args=["admin"]),
            reverse("usuario_desactivar", args=["admin"]),
            reverse("usuario_reactivar", args=["admin"]),
            reverse("usuario_contrasena", args=["admin"]),
            reverse("auditoria_descargar", args=["pdf"]),
            reverse("auditoria_descargar", args=["excel"]),
        ]

        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        respuesta = self.client.post(
            reverse("usuario_desactivar", args=["admin"])
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Usuario.objects.get(username="admin").activo)
        respuesta = self.client.post(
            reverse("usuario_contrasena", args=["admin"]),
            {"contrasena": CLAVE + "x", "confirmacion": CLAVE + "x"},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(
            Usuario.objects.get(username="admin").check_password(CLAVE)
        )

    def test_alta_crea_cuenta_con_contrasena_y_registra(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(reverse("usuario_nuevo"), {
            "username": "nuevo", "nombre_completo": "Nuevo Usuario",
            "rol": Rol.CONTADOR_GENERAL, "contrasena": CLAVE,
            "confirmacion": CLAVE,
        })

        self.assertRedirects(respuesta, reverse("users"))
        nuevo = Usuario.objects.get(username="nuevo")
        self.assertTrue(nuevo.check_password(CLAVE))
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.ALTA_USUARIO)
        self.assertEqual(registro.afectado, nuevo)
        self.client.logout()
        login = self.client.post(
            reverse("login"), {"username": "nuevo", "password": CLAVE}
        )
        self.assertRedirects(login, reverse("dashboard"))

    def test_alta_duplicada_se_senala_junto_al_campo(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(reverse("usuario_nuevo"), {
            "username": "cont", "nombre_completo": "Otro",
            "rol": Rol.CONTADOR_GENERAL,
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "form-error")
        self.assertContains(respuesta, 'value="Otro"')

    def test_cuenta_desactivada_no_puede_iniciar_sesion(self):
        self.client.force_login(self.admin)
        url = reverse("usuario_desactivar", args=["cont"])

        self.assertContains(self.client.get(url), "Confirmar desactivación")
        self.assertRedirects(self.client.post(url), reverse("users"))
        self.assertFalse(Usuario.objects.get(username="cont").activo)
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.DESACTIVACION_USUARIO)
        self.client.logout()

        respuesta = self.client.post(
            reverse("login"), {"username": "cont", "password": CLAVE}
        )

        self.assertContains(respuesta, CUENTA_NO_HABILITADA)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_desactivar_cuenta_inactiva_informa_la_causa(self):
        Usuario.objects.filter(username="cont").update(activo=False)
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("usuario_desactivar", args=["cont"]), follow=True
        )

        self.assertContains(respuesta, "El usuario ya está inactivo.")

    def test_reactivar_permite_volver_a_iniciar_sesion(self):
        Usuario.objects.filter(username="cont").update(activo=False)
        self.client.force_login(self.admin)
        url = reverse("usuario_reactivar", args=["cont"])

        self.assertContains(self.client.get(url), "Confirmar reactivación")
        self.assertRedirects(self.client.post(url), reverse("users"))
        self.assertTrue(Usuario.objects.get(username="cont").activo)
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.REACTIVACION_USUARIO)
        self.client.logout()

        respuesta = self.client.post(
            reverse("login"), {"username": "cont", "password": CLAVE}
        )

        self.assertRedirects(respuesta, reverse("dashboard"))

    def test_reactivar_cuenta_activa_informa_la_causa(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("usuario_reactivar", args=["cont"]), follow=True
        )

        self.assertContains(respuesta, "El usuario ya está activo.")

    def test_cambiar_contrasena_reemplaza_la_anterior(self):
        self.client.force_login(self.admin)
        url = reverse("usuario_contrasena", args=["cont"])
        nueva = CLAVE + "-nueva"

        self.assertContains(
            self.client.get(url), "Confirmar cambio de contraseña"
        )
        respuesta = self.client.post(
            url, {"contrasena": nueva, "confirmacion": nueva}
        )

        self.assertRedirects(respuesta, reverse("users"))
        registro = RegistroBitacora.objects.latest("id")
        self.assertEqual(registro.accion, Accion.CAMBIO_CONTRASENA)
        self.assertEqual(registro.afectado.username, "cont")
        self.client.logout()
        anterior = self.client.post(
            reverse("login"), {"username": "cont", "password": CLAVE}
        )
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(anterior.status_code, 200)
        login = self.client.post(
            reverse("login"), {"username": "cont", "password": nueva}
        )
        self.assertRedirects(login, reverse("dashboard"))

    def test_cambiar_contrasena_con_error_no_la_reemplaza(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("usuario_contrasena", args=["cont"]),
            {"contrasena": CLAVE + "a", "confirmacion": CLAVE + "b"},
        )

        self.assertContains(respuesta, "Las contraseñas no coinciden.")
        self.assertNotContains(respuesta, CLAVE + "a")
        self.assertTrue(
            Usuario.objects.get(username="cont").check_password(CLAVE)
        )

    def test_descargas_devuelven_archivo_no_vacio(self):
        RegistroBitacora.objects.create(
            accion=Accion.INICIO_SESION, resultado=Resultado.EXITOSO,
            actor=self.admin,
        )
        self.client.force_login(self.admin)
        tipos = {
            "pdf": "application/pdf",
            "excel": "application/vnd.openxmlformats-officedocument."
                     "spreadsheetml.sheet",
        }
        total = RegistroBitacora.objects.count()

        for formato, tipo in tipos.items():
            respuesta = self.client.get(
                reverse("auditoria_descargar", args=[formato])
            )

            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta["Content-Type"], tipo)
            self.assertIn("attachment;", respuesta["Content-Disposition"])
            self.assertGreater(len(respuesta.content), 0)
        self.assertEqual(RegistroBitacora.objects.count(), total)
