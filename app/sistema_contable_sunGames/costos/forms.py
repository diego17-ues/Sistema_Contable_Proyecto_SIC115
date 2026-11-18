"""Formularios del módulo de costos (validación de formato)."""

import uuid
from decimal import Decimal

from django import forms

FECHA_FORMATOS = ["%Y-%m-%d", "%d/%m/%Y"]


def _fecha(**kwargs):
    return forms.DateField(
        input_formats=FECHA_FORMATOS,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        **kwargs,
    )


def _decimal(max_digits, decimal_places, minimo="0.01", **kwargs):
    return forms.DecimalField(
        max_digits=max_digits, decimal_places=decimal_places,
        min_value=Decimal(minimo),
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": minimo, "inputmode": "decimal",
            "class": "money-input",
        }),
        **kwargs,
    )


def _cuenta(cuenta):
    return f"{cuenta.codigo} · {cuenta.denominacion}"


def nueva_clave():
    return uuid.uuid4().hex


class ClaveForm(forms.Form):
    """Clave de idempotencia: se genera al abrir el modal y viaja oculta;
    un segundo envío del mismo formulario no duplica nada."""

    clave = forms.CharField(max_length=80, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.setdefault("clave", nueva_clave())


class FiltroOrdenForm(forms.Form):
    ESTADOS = [("", "Todos"), ("ABIERTA", "Abiertas"),
               ("CERRADA", "Cerradas")]
    estado = forms.ChoiceField(choices=ESTADOS, required=False)


class OrdenForm(forms.Form):
    nombre_juego = forms.CharField(
        label="Juego", max_length=160,
        widget=forms.TextInput(attrs={"placeholder": "Ej. Neo Drift"}),
    )
    fecha_inicio = _fecha(label="Fecha de inicio")


class _RegistroForm(ClaveForm):
    def __init__(self, *args, procesos=(), configuracion=None,
                 proceso_obligatorio=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.procesos = list(procesos)
        vacio = "— Seleccione —" if proceso_obligatorio else "— Sin proceso —"
        self.fields["proceso"].required = proceso_obligatorio
        self.fields["proceso"].choices = [("", vacio)] + [
            (p.pk, p.nombre) for p in self.procesos
        ]
        contrapartidas = (list(configuracion.contrapartidas.all())
                          if configuracion else [])
        self.fields["contrapartida"].choices = [
            (c.pk, _cuenta(c)) for c in contrapartidas
        ]
        if configuracion and not self.is_bound:
            self.initial.setdefault(
                "contrapartida", configuracion.contrapartida_defecto_id
            )

    fecha = _fecha(label="Fecha")
    proceso = forms.ChoiceField(label="Proceso")
    contrapartida = forms.ChoiceField(label="Contrapartida (haber)")


class ManoObraForm(_RegistroForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, proceso_obligatorio=True, **kwargs)

    horas = _decimal(10, 2, label="Horas")
    costo_hora = _decimal(
        12, 4, label="Costo por hora (USD)",
        help_text="Se propone según el proceso; puedes ajustarlo.",
    )
    field_order = ["fecha", "proceso", "horas", "costo_hora",
                   "contrapartida", "clave"]


class CostoForm(_RegistroForm):
    descripcion = forms.CharField(label="Descripción", max_length=200)
    importe = _decimal(14, 2, label="Monto (USD)")
    field_order = ["fecha", "proceso", "descripcion", "importe",
                   "contrapartida", "clave"]


class AnularForm(ClaveForm):
    motivo = forms.CharField(label="Motivo de la anulación", max_length=200)


class ProcesoForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=120)
    descripcion = forms.CharField(label="Descripción", max_length=200,
                                  required=False)
    costo_hora = _decimal(12, 4, minimo="0", label="Costo por hora (USD)",
                          required=False)


class ProcesoEditForm(forms.Form):
    costo_hora = _decimal(12, 4, minimo="0", label="Costo por hora (USD)",
                          required=False)
    activo = forms.BooleanField(label="Activo", required=False)


class ConfiguracionCuentaForm(forms.Form):
    def __init__(self, *args, cuentas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.cuentas = {str(c.pk): c for c in cuentas}
        opciones = [(pk, _cuenta(c)) for pk, c in self.cuentas.items()]
        vacio = [("", "— Seleccione —")]
        self.fields["cuenta_costo"].choices = vacio + opciones
        self.fields["contrapartidas"].choices = opciones
        self.fields["contrapartida_defecto"].choices = (
            [("", "— Seleccione —")] + opciones
        )

    cuenta_costo = forms.ChoiceField(label="Cuenta de costo (debe)")
    contrapartidas = forms.MultipleChoiceField(
        label="Contrapartidas permitidas (haber)",
        widget=forms.SelectMultiple(attrs={"size": "6"}),
    )
    contrapartida_defecto = forms.ChoiceField(
        label="Contrapartida por defecto"
    )

    def cuentas_elegidas(self):
        datos = self.cleaned_data
        return (
            self.cuentas[datos["cuenta_costo"]],
            [self.cuentas[pk] for pk in datos["contrapartidas"]],
            self.cuentas[datos["contrapartida_defecto"]],
        )


class LicenciasForm(forms.Form):
    licencias_estimadas = forms.IntegerField(
        label="Licencias estimadas", min_value=1,
        widget=forms.NumberInput(attrs={"min": "1", "step": "1",
                                        "inputmode": "numeric"}),
    )


class EstimacionRefForm(forms.Form):
    def __init__(self, *args, versiones=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["version"].choices = [("", "— Sin vínculo —")] + [
            (v.pk, f"{v.juego.nombre} · versión {v.numero} "
                   f"({v.get_estado_display().lower()})")
            for v in versiones
        ]

    version = forms.ChoiceField(
        label="Versión de presupuesto aprobada", required=False,
        help_text="Solo lectura: muestra el total estimado, sin variación.",
    )
