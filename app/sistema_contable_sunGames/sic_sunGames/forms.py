from django import forms

CAMPO_OBLIGATORIO = "Este campo es obligatorio."


class LoginForm(forms.Form):
    """CU-01: valida que Usuario y Contraseña no estén vacíos."""

    username = forms.CharField(
        label="Usuario",
        error_messages={"required": CAMPO_OBLIGATORIO},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": "Nombre de usuario",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        error_messages={"required": CAMPO_OBLIGATORIO},
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Contraseña",
            },
        ),
    )
