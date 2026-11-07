from django.test import SimpleTestCase

from usuarios.forms import UsuarioAltaForm
from usuarios.roles import Rol


class UsuarioAltaFormTest(SimpleTestCase):
    """CU-02.1 Formulario de alta."""

    def datos(self, **cambios):
        datos = {
            "username": "jperez",
            "nombre_completo": "Juan Pérez",
            "rol": Rol.CONTADOR_GENERAL,
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
        for campo in ("username", "nombre_completo", "rol"):
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

    def test_conserva_los_valores_validos_ante_un_error(self):
        form = UsuarioAltaForm(data=self.datos(username=""))

        self.assertFalse(form.is_valid())
        self.assertEqual(form["nombre_completo"].value(), "Juan Pérez")
        self.assertEqual(form["rol"].value(), Rol.CONTADOR_GENERAL)

    def test_roles_disponibles_excluyen_contador_de_costos(self):
        choices = UsuarioAltaForm().fields["rol"].choices
        etiquetas = [etiqueta for _, etiqueta in choices]

        self.assertEqual(etiquetas, ["Administrador", "Contador General"])
