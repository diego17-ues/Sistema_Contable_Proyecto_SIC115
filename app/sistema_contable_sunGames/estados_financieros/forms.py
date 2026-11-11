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
        label="Confirmación", required=False, max_length=NOMBRE_MAX,
        strip=False,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    motivo = campo_motivo()


class ReaperturaPeriodoForm(forms.Form):
    contrasena = forms.CharField(
        label="Contraseña del administrador", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    motivo = campo_motivo()


class RangoForm(forms.Form):
    desde = forms.DateField()
    hasta = forms.DateField()


class CierreRangoForm(RangoForm, CierrePeriodoForm):
    tipo_cierre = forms.ChoiceField(
        choices=(("provisional", "Cierre provisional"),
                 ("anual", "Cierre anual")),
        required=False,
        initial="provisional",
    )


class AjusteForm(forms.Form):
    code = forms.CharField(max_length=4)
    date = forms.DateField()
    concept = forms.CharField(max_length=200, required=False)
    reference = forms.CharField(max_length=40, required=False)
    debit = forms.DecimalField(required=False, decimal_places=2,
                               max_digits=14)
    credit = forms.DecimalField(required=False, decimal_places=2,
                                max_digits=14)
