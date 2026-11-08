from django import forms

FECHA_INVALIDA = "Ingrese una fecha válida."
FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y"]


def _fecha(label):
    return forms.DateField(
        label=label, required=False, input_formats=FORMATOS_FECHA,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"invalid": FECHA_INVALIDA},
    )


def _selector_de_cuenta(cuentas):
    opciones = [("", "Seleccione")] + [
        (c.codigo, f"{c.codigo} · {c.denominacion}") for c in cuentas
    ]
    return forms.Select(choices=opciones)


class TransaccionForm(forms.Form):
    """Formato de la cabecera; las reglas se validan en el servicio."""

    fecha = _fecha("Fecha")
    concepto = forms.CharField(label="Concepto", required=False, strip=False)


class MovimientoForm(forms.Form):
    cuenta = forms.CharField(label="Cuenta", required=False)
    importe = forms.CharField(
        label="Importe", required=False, strip=False,
        widget=forms.TextInput(
            attrs={"inputmode": "decimal", "placeholder": "0.00"}
        ),
    )

    def __init__(self, *args, cuentas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].widget = _selector_de_cuenta(cuentas)


MovimientoFormSet = forms.formset_factory(MovimientoForm, extra=3)


class ConsultaMayorForm(forms.Form):
    cuenta = forms.CharField(label="Cuenta", required=False)
    desde = _fecha("Desde")
    hasta = _fecha("Hasta")

    def __init__(self, *args, cuentas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].widget = _selector_de_cuenta(cuentas)


class SaldoForm(forms.Form):
    cuenta = forms.CharField(label="Cuenta", required=False)
    fecha_corte = _fecha("Fecha de corte")

    def __init__(self, *args, cuentas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].widget = _selector_de_cuenta(cuentas)
