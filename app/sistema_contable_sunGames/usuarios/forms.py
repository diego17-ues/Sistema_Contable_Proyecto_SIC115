from django import forms

from .models import NOMBRE_COMPLETO_MAX_LENGTH, USERNAME_MAX_LENGTH
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
    rol = forms.ChoiceField(
        label="Rol",
        choices=Rol.choices,
        error_messages={
            "required": CAMPO_OBLIGATORIO,
            "invalid_choice": "Seleccione un rol permitido.",
        },
    )
