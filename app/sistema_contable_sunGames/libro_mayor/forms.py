from django import forms
from django.utils import timezone

from .models import TipoMovimiento

FECHA_INVALIDA = "Ingrese una fecha válida."
FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y"]


def _fecha(label, initial=None, attrs=None):
    return forms.DateField(
        label=label, required=False, input_formats=FORMATOS_FECHA,
        initial=initial,
        widget=forms.DateInput(
            attrs={"type": "date", **(attrs or {})}, format="%Y-%m-%d"
        ),
        error_messages={"invalid": FECHA_INVALIDA},
    )


def _monto(label, clase):
    return forms.CharField(
        label=label, required=False,
        widget=forms.TextInput(attrs={
            "type": "number", "min": "0", "step": "0.01",
            "class": f"{clase} money-input", "aria-label": label,
        }),
    )


def _texto(label, clase):
    return forms.CharField(
        label=label, required=False, strip=False,
        widget=forms.TextInput(attrs={"class": clase, "aria-label": label}),
    )


class ConsultaMayorForm(forms.Form):
    """Cuenta del Libro Mayor y rango de fechas del detalle."""

    cuenta = forms.CharField(label="Cuenta del Libro Mayor", required=False)
    desde = _fecha("Desde", attrs={"id": "ledgerFrom"})
    hasta = _fecha("Hasta", attrs={"id": "ledgerTo"})

    def __init__(self, *args, cuentas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].widget = forms.Select(
            choices=[
                (c.codigo, f"{c.codigo} · {c.denominacion}") for c in cuentas
            ],
            attrs={"id": "ledgerAccountFilter", "data-ledger-account": ""},
        )


class RegistroMayorForm(forms.Form):
    """Cuenta seleccionada en la que se registran las líneas."""

    cuenta = forms.CharField(required=False, widget=forms.HiddenInput)
    desde = forms.DateField(
        required=False, input_formats=FORMATOS_FECHA,
        widget=forms.HiddenInput,
    )
    hasta = forms.DateField(
        required=False, input_formats=FORMATOS_FECHA,
        widget=forms.HiddenInput,
    )


class MovimientoForm(forms.Form):
    """Formato de una línea; las reglas se validan en el servicio."""

    fecha = _fecha(
        "Fecha", initial=timezone.localdate,
        attrs={"class": "ledger-line-date", "aria-label": "Fecha"},
    )
    concepto = _texto("Descripción", "ledger-line-concept")
    referencia = _texto("Referencia", "ledger-line-reference")
    tipo = forms.ChoiceField(
        label="Tipo de transacción", required=False,
        choices=[("", "Tipo")] + TipoMovimiento.choices,
        error_messages={"invalid_choice": "El tipo de transacción no es "
                                          "válido."},
        widget=forms.Select(attrs={
            "class": "ledger-line-type", "aria-label": "Tipo de transacción",
        }),
    )
    debe = _monto("Debe", "ledger-line-debit")
    haber = _monto("Haber", "ledger-line-credit")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Toda línea enviada se valida, aunque conserve la fecha inicial.
        self.empty_permitted = False


MovimientoFormSet = forms.formset_factory(MovimientoForm, extra=1)


class BalanceComprobacionForm(forms.Form):
    corte = _fecha(
        "Fecha de corte", initial=timezone.localdate,
        attrs={"id": "trialBalanceTo"},
    )
