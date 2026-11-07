from unittest.mock import patch

from django.contrib.auth import SESSION_KEY
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from bitacora.eventos import Accion, Resultado
from bitacora.models import RegistroBitacora
from usuarios.autenticacion import AutenticadorDjango
from usuarios.exceptions import ServicioAutenticacionError
from usuarios.models import Usuario
from usuarios.roles import Rol

from .forms import LoginForm

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
        usuario.set_password("clave-1")
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
        respuesta = self.post("contador", "clave-1")

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

        respuesta = self.post("inactivo", "clave-1")

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
            respuesta = self.post("contador", "clave-1")

        self.assertContains(respuesta, FALLA_SERVICIO)
        self.assert_sin_sesion()
        self.assertEqual(
            self.ultimo_registro().resultado, Resultado.ERROR_SERVICIO
        )

    def test_administrador_queda_sin_area_inicial(self):
        self.crear_usuario("admin", Rol.ADMINISTRADOR)

        respuesta = self.post("admin", "clave-1")

        self.assertContains(
            respuesta, "El área inicial de su rol todavía no está disponible."
        )
        self.assertNotContains(respuesta, 'id="sidebar"')
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
