from django.test import SimpleTestCase

from usuarios.forms import CambioContrasenaForm, UsuarioAltaForm
from usuarios.models import Usuario
from usuarios.roles import Rol

from .fakes import CLAVE_NUEVA


class UsuarioAltaFormTest(SimpleTestCase):
    """CU-02.1 Formulario de alta."""

    def datos(self, **cambios):
        datos = {
            "username": "jperez",
            "nombre_completo": "Juan Pérez",
            "rol": Rol.CONTADOR_GENERAL,
            "contrasena": CLAVE_NUEVA,
            "confirmacion": CLAVE_NUEVA,
        }
        datos.update(cambios)
        return datos

    def test_datos_validos(self):
        form = UsuarioAltaForm(data=self.datos())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["username"], "jperez")

    def test_campos_obligatorios(self):
        form = UsuarioAltaForm(data={})

        self.assertFalse(form.is_valid())
        for campo in ("username", "nombre_completo", "rol", "contrasena",
                      "confirmacion"):
            self.assertEqual(
                form.errors[campo], ["Este campo es obligatorio."]
            )

    def test_username_admite_hasta_ocho_caracteres(self):
        form = UsuarioAltaForm(data=self.datos(username="a" * 8))
        self.assertTrue(form.is_valid())

        form = UsuarioAltaForm(data=self.datos(username="a" * 9))

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["username"],
            ["El nombre de usuario admite hasta 8 caracteres."],
        )

    def test_rol_no_valido(self):
        form = UsuarioAltaForm(data=self.datos(rol="CONTADOR_COSTOS"))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["rol"], ["Seleccione un rol permitido."])

    def test_confirmacion_distinta(self):
        form = UsuarioAltaForm(data=self.datos(confirmacion="otra-cosa-99"))

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["confirmacion"], ["Las contraseñas no coinciden."]
        )

    def test_contrasena_debil_rechazada_en_espanol(self):
        form = UsuarioAltaForm(
            data=self.datos(contrasena="12345", confirmacion="12345")
        )

        self.assertFalse(form.is_valid())
        self.assertTrue(
            any("contraseña" in error for error in form.errors["contrasena"])
        )

    def test_no_entrega_la_confirmacion_al_servicio(self):
        form = UsuarioAltaForm(data=self.datos())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("confirmacion", form.cleaned_data)
        self.assertEqual(form.cleaned_data["contrasena"], CLAVE_NUEVA)

    def test_no_vuelve_a_mostrar_la_contrasena(self):
        form = UsuarioAltaForm(data=self.datos(username=""))

        self.assertFalse(form.is_valid())
        self.assertNotIn(CLAVE_NUEVA, str(form))

    def test_conserva_los_valores_validos_ante_un_error(self):
        form = UsuarioAltaForm(data=self.datos(username=""))

        self.assertFalse(form.is_valid())
        self.assertEqual(form["nombre_completo"].value(), "Juan Pérez")
        self.assertEqual(form["rol"].value(), Rol.CONTADOR_GENERAL)

    def test_roles_disponibles_excluyen_contador_de_costos(self):
        choices = UsuarioAltaForm().fields["rol"].choices
        etiquetas = [etiqueta for _, etiqueta in choices]

        self.assertEqual(etiquetas, ["Administrador", "Contador General"])


class CambioContrasenaFormTest(SimpleTestCase):
    def setUp(self):
        self.usuario = Usuario(username="jperez", nombre_completo="Juan")

    def form(self, contrasena, confirmacion):
        return CambioContrasenaForm(
            data={"contrasena": contrasena, "confirmacion": confirmacion},
            usuario=self.usuario,
        )

    def test_datos_validos(self):
        form = self.form(CLAVE_NUEVA, CLAVE_NUEVA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data, {"contrasena": CLAVE_NUEVA})

    def test_campos_obligatorios(self):
        form = self.form("", "")

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["contrasena"], ["Este campo es obligatorio."]
        )

    def test_confirmacion_distinta(self):
        form = self.form(CLAVE_NUEVA, CLAVE_NUEVA + "x")

        self.assertEqual(
            form.errors["confirmacion"], ["Las contraseñas no coinciden."]
        )

    def test_rechaza_contrasena_parecida_al_usuario(self):
        form = self.form("jperez2026", "jperez2026")

        self.assertFalse(form.is_valid())
        self.assertIn("contrasena", form.errors)
