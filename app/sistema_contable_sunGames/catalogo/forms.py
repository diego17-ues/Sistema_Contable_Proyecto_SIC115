from django import forms
from django.core.validators import RegexValidator

from .models import CODIGO_LENGTH, DENOMINACION_MAX_LENGTH

CAMPO_OBLIGATORIO = "Este campo es obligatorio."
OPCION_INVALIDA = "Seleccione una opción válida."
CODIGO_INVALIDO = "El código admite solo dígitos, hasta 4."


def _opciones(elementos, vacio):
    return [("", vacio)] + [(e.codigo, str(e)) for e in elementos]


def _seleccion(label, required=True):
    return forms.ChoiceField(
        label=label, required=required,
        error_messages={
            "required": CAMPO_OBLIGATORIO, "invalid_choice": OPCION_INVALIDA,
        },
    )


class CuentaFiltroForm(forms.Form):
    """Filtros de la consulta del catálogo (CU-06)."""

    ESTADOS = {"activa": True, "inactiva": False}

    codigo = forms.CharField(
        label="Código", required=False, max_length=CODIGO_LENGTH,
        validators=[RegexValidator(r"^[0-9]+$", CODIGO_INVALIDO)],
        error_messages={"max_length": CODIGO_INVALIDO},
        widget=forms.TextInput(
            attrs={"placeholder": "Ej. 1101", "inputmode": "numeric"}
        ),
    )
    denominacion = forms.CharField(
        label="Denominación", required=False,
        max_length=DENOMINACION_MAX_LENGTH,
        widget=forms.TextInput(attrs={"placeholder": "Denominación"}),
    )
    rubro = _seleccion("Rubro", required=False)
    naturaleza = _seleccion("Naturaleza", required=False)
    estado = forms.ChoiceField(
        label="Estado", required=False,
        choices=[
            ("", "Todos"), ("activa", "Activa"), ("inactiva", "Inactiva")
        ],
        error_messages={"invalid_choice": OPCION_INVALIDA},
    )

    def __init__(self, *args, rubros, naturalezas, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rubro"].choices = _opciones(rubros, "Todos")
        self.fields["naturaleza"].choices = _opciones(naturalezas, "Todas")

    def filtros(self):
        if not self.is_bound:
            return {}
        datos = self.cleaned_data
        return {
            "codigo": datos["codigo"],
            "denominacion": datos["denominacion"],
            "rubro": datos["rubro"],
            "naturaleza": datos["naturaleza"],
            "activa": self.ESTADOS.get(datos["estado"]),
        }


class CuentaForm(forms.Form):
    """Datos y documentación de CU-06.1 y CU-06.3; sin campo de código."""

    CAMPOS_CUENTA = (
        "denominacion", "rubro", "naturaleza", "descripcion", "reglas_uso"
    )

    denominacion = forms.CharField(
        label="Denominación", max_length=DENOMINACION_MAX_LENGTH,
        error_messages={
            "required": CAMPO_OBLIGATORIO,
            "max_length": "La denominación admite hasta 150 caracteres.",
        },
    )
    rubro = _seleccion("Rubro")
    naturaleza = _seleccion("Naturaleza")
    descripcion = forms.CharField(
        label="Descripción", required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    reglas_uso = forms.CharField(
        label="Reglas de uso", required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    justificacion = forms.CharField(
        label="Justificación", widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    referencia_respaldo = forms.CharField(
        label="Referencia de respaldo", max_length=150,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    acuerdo_numero = forms.CharField(
        label="N.º de acuerdo de Junta Directiva", max_length=50,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    acuerdo_fecha = forms.DateField(
        label="Fecha del acuerdo",
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={
            "required": CAMPO_OBLIGATORIO,
            "invalid": "Ingrese una fecha válida.",
        },
    )

    def __init__(self, *args, rubros, naturalezas, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rubro"].choices = _opciones(rubros, "Seleccione")
        self.fields["naturaleza"].choices = _opciones(
            naturalezas, "Seleccione"
        )

    def campos_cuenta(self):
        return [self[nombre] for nombre in self.CAMPOS_CUENTA]

    def campos_documentacion(self):
        return [
            campo for campo in self if campo.name not in self.CAMPOS_CUENTA
        ]
