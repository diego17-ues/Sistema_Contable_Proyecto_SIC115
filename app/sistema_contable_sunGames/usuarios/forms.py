from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils import translation

from .models import (
    NOMBRE_COMPLETO_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    Usuario,
)
from .roles import Rol

CAMPO_OBLIGATORIO = "Este campo es obligatorio."


class UsuarioAltaForm(forms.Form):
    """CU-02.1: valida el formato del alta.

    La unicidad y la autorización las valida UsuarioService.
    """

    username = forms.CharField(
        label="Nombre de usuario",
        max_length=USERNAME_MAX_LENGTH,
        error_messages={
            "required": CAMPO_OBLIGATORIO,
            "max_length": (
                f"El nombre de usuario admite hasta {USERNAME_MAX_LENGTH} "
                "caracteres."
            ),
        },
    )
    nombre_completo = forms.CharField(
        label="Nombre completo",
        max_length=NOMBRE_COMPLETO_MAX_LENGTH,
        error_messages={
            "required": CAMPO_OBLIGATORIO,
            "max_length": (
                "El nombre completo admite hasta "
                f"{NOMBRE_COMPLETO_MAX_LENGTH} caracteres."
            ),
        },
    )
    contrasena = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    confirmacion = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    rol = forms.ChoiceField(
        label="Rol",
        choices=Rol.choices,
        error_messages={
            "required": CAMPO_OBLIGATORIO,
            "invalid_choice": "Seleccione un rol permitido.",
        },
    )

    def clean(self):
        datos = super().clean()
        contrasena = datos.get("contrasena")
        confirmacion = datos.pop("confirmacion", None)
        if not contrasena or confirmacion is None:
            return datos
        if contrasena != confirmacion:
            self.add_error("confirmacion", "Las contraseñas no coinciden.")
            return datos
        candidato = Usuario(
            username=datos.get("username", ""),
            nombre_completo=datos.get("nombre_completo", ""),
        )
        with translation.override("es"):
            try:
                validate_password(contrasena, user=candidato)
            except forms.ValidationError as error:
                self.add_error("contrasena", list(error.messages))
        return datos
