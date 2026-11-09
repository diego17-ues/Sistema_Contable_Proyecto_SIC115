from django import forms

from libro_mayor.models import PeriodoContable

from .services import MOTIVO_MAX

NOMBRE_MAX = PeriodoContable._meta.get_field("nombre").max_length


def campo_motivo():
    return forms.CharField(
        label="Motivo", required=False, max_length=MOTIVO_MAX,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class CierrePeriodoForm(forms.Form):
    confirmacion = forms.CharField(
        label="Nombre del período", required=False, max_length=NOMBRE_MAX,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    motivo = campo_motivo()


class ReaperturaPeriodoForm(forms.Form):
    contrasena = forms.CharField(
        label="Contraseña del administrador", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    motivo = campo_motivo()
