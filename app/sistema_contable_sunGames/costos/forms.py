"""Formularios del módulo de costos (validación de formato)."""

from django import forms

from .models import CONCEPTOS_CUENTA, TIPOS_USO_EQUIPO, CargoOrden

FECHA_FORMATOS = ["%Y-%m-%d", "%d/%m/%Y"]


def _fecha(**kwargs):
    return forms.DateField(
        input_formats=FECHA_FORMATOS,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        **kwargs,
    )


def _decimal(max_digits, decimal_places, **kwargs):
    return forms.DecimalField(
        max_digits=max_digits, decimal_places=decimal_places,
        min_value=0, **kwargs,
    )


def _opciones(queryset, vacio="— Seleccione —", texto=lambda o: str(o)):
    return [("", vacio)] + [(o.pk, texto(o)) for o in queryset]


class FiltroOrdenForm(forms.Form):
    ESTADOS = [("", "Todos"), ("ABIERTA", "Abiertas"),
               ("CERRADA", "Cerradas")]
    estado = forms.ChoiceField(choices=ESTADOS, required=False)


class OrdenForm(forms.Form):
    nombre_juego = forms.CharField(
        label="Nombre del juego", max_length=160,
        widget=forms.TextInput(attrs={"placeholder": "Ej. Neo Drift"}),
    )
    capitalizable_desde = _fecha(
        label="Capitalizable desde", required=False,
        help_text="Fecha desde la que los costos se capitalizan "
                  "(criterio NIC 38). Vacío: nada se capitaliza.",
    )


class HoraForm(forms.Form):
    def __init__(self, *args, procesos=None, roles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proceso"].choices = (
            [("", "— Sin proceso —")]
            + [(p.pk, p.nombre) for p in (procesos or [])]
        )
        self.fields["rol"].choices = [
            (r, r) for r in (roles or [])
        ] or [("", "— Sin roles con salario —")]

    proceso = forms.ChoiceField(label="Proceso", required=False)
    rol = forms.ChoiceField(label="Rol")
    horas = _decimal(10, 2, label="Horas")
    fecha = _fecha(label="Fecha")


class CargoForm(forms.Form):
    ORIGENES = [
        (CargoOrden.ORIGEN_DIRECTO, "Directo"),
        (CargoOrden.ORIGEN_SERVICIO, "Servicio asignado"),
        (CargoOrden.ORIGEN_AJUSTE, "Ajuste"),
    ]
    origen = forms.ChoiceField(choices=ORIGENES, label="Origen")
    afecta_mayor = forms.BooleanField(
        label="Afecta al mayor (capitalizable)", required=False,
        initial=True,
    )
    concepto_cuenta = forms.ChoiceField(
        choices=CONCEPTOS_CUENTA, required=False,
        label="Cuenta de costos",
    )
    monto = _decimal(14, 2, label="Monto (USD)")
    fecha = _fecha(label="Fecha")
    descripcion = forms.CharField(
        label="Descripción", max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Concepto del cargo"}),
    )


class FondoForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=120)
    monto = _decimal(14, 2, label="Monto (USD)")
    fecha = _fecha(label="Fecha")
    descripcion = forms.CharField(
        label="Descripción", max_length=200, required=False,
    )


class EquipoForm(forms.Form):
    def __init__(self, *args, ordenes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["orden"].choices = (
            [("", "— No exclusivo —")]
            + [(o.pk, str(o)) for o in (ordenes or [])]
        )

    nombre = forms.CharField(label="Nombre", max_length=120)
    costo = _decimal(14, 2, label="Costo (USD)")
    valor_residual = _decimal(14, 2, label="Valor residual (USD)",
                              required=False, initial=0)
    vida_util_meses = forms.IntegerField(
        label="Vida útil (meses)", min_value=1,
    )
    tipo_uso = forms.ChoiceField(choices=TIPOS_USO_EQUIPO, label="Tipo de uso")
    orden = forms.ChoiceField(label="Orden exclusiva", required=False)
    horas_mes = _decimal(10, 2, label="Horas máquina por mes",
                         required=False, initial=0)
    fecha_adquisicion = _fecha(label="Fecha de adquisición")


class UsoEquipoForm(forms.Form):
    def __init__(self, *args, ordenes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["orden"].choices = _opciones(ordenes or [], "Orden")

    equipo = forms.IntegerField(widget=forms.HiddenInput)
    orden = forms.ChoiceField(label="Orden de trabajo")
    fecha = _fecha(label="Fecha")
    horas = _decimal(10, 2, label="Horas máquina")


class ProcesoForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=120)
    descripcion = forms.CharField(
        label="Descripción", max_length=200, required=False,
    )


class CostoProcesoForm(forms.Form):
    def __init__(self, *args, procesos=None, periodos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proceso"].choices = _opciones(procesos or [], "Proceso")
        self.fields["periodo"].choices = _opciones(periodos or [], "Período")

    proceso = forms.ChoiceField(label="Proceso")
    periodo = forms.ChoiceField(label="Período")
    costo = _decimal(14, 2, label="Costo del proceso (USD)")
    horas_base = _decimal(10, 2, label="Horas base")
    tasa_presupuestada = forms.DecimalField(
        label="Tasa presupuestada", max_digits=12, decimal_places=6,
        min_value=0, required=False,
    )


class ParametroForm(forms.Form):
    concepto = forms.CharField(label="Concepto", max_length=60)
    valor = forms.DecimalField(
        label="Valor", max_digits=12, decimal_places=6, min_value=0,
    )
    vigente_desde = _fecha(label="Vigente desde")
    vigente_hasta = _fecha(label="Vigente hasta", required=False)
    verificado = forms.BooleanField(
        label="Verificado", required=False,
        help_text="Las tasas laborales/tributarias siempre quedan "
                  "marcadas como VERIFICAR hasta confirmarlas.",
    )
    descripcion = forms.CharField(
        label="Descripción", max_length=200, required=False,
    )


class SalarioForm(forms.Form):
    rol = forms.CharField(label="Rol", max_length=60)
    salario_bruto = forms.DecimalField(
        label="Salario bruto (USD)", max_digits=12, decimal_places=2,
        min_value=0,
    )
    vigente_desde = _fecha(label="Vigente desde")
    vigente_hasta = _fecha(label="Vigente hasta", required=False)
    verificado = forms.BooleanField(label="Verificado", required=False)


class MapeoForm(forms.Form):
    def __init__(self, *args, cuentas=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].choices = [
            (c.codigo, f"{c.codigo} · {c.denominacion}")
            for c in (cuentas or [])
        ]

    concepto = forms.ChoiceField(choices=CONCEPTOS_CUENTA, label="Concepto")
    cuenta = forms.ChoiceField(label="Cuenta del catálogo")


class TasasForm(forms.Form):
    def __init__(self, *args, periodos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periodo"].choices = _opciones(periodos or [], "Período")

    periodo = forms.ChoiceField(label="Período")
    usar_presupuestada = forms.BooleanField(
        label="Usar tasa presupuestada", required=False,
    )


class DepreciacionForm(forms.Form):
    anio = forms.IntegerField(label="Año", min_value=2000, max_value=2100)
    mes = forms.IntegerField(label="Mes", min_value=1, max_value=12)


class CorteForm(forms.Form):
    TIPOS = [
        ("PROVISIONAL", "Provisional (reversible)"),
        ("DEFINITIVO", "Definitivo (no se revierte)"),
    ]

    def __init__(self, *args, periodos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periodo"].choices = _opciones(periodos or [], "Período")

    tipo = forms.ChoiceField(choices=TIPOS, label="Tipo de corte")
    periodo = forms.ChoiceField(label="Período")
    motivo = forms.CharField(label="Motivo", max_length=200)


class ConfirmForm(forms.Form):
    confirmacion = forms.CharField(label="Confirmación")
    motivo = forms.CharField(
        label="Motivo", max_length=200,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
