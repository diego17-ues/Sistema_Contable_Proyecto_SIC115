from decimal import Decimal, InvalidOperation

from django import forms

CAMPO_OBLIGATORIO = "Este campo es obligatorio."
FECHA_INVALIDA = "Ingrese una fecha válida."
FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y"]


def _fecha(label, required=True):
    return forms.DateField(
        label=label,
        required=required,
        input_formats=FORMATOS_FECHA,
        widget=forms.DateInput(
            attrs={"type": "date"}, format="%Y-%m-%d"
        ),
        error_messages={
            "required": CAMPO_OBLIGATORIO, "invalid": FECHA_INVALIDA,
        },
    )


class JuegoForm(forms.Form):
    """Alta de juego; las fases fijas de SunGames se crean solas."""

    nombre = forms.CharField(
        label="Nombre del juego",
        max_length=150,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )


class EstimacionMatrizForm(forms.Form):
    """Matriz PERT de un experto y rol para todas las fases del juego.

    Cada fase tiene sus campos optimista/moda/pesimista; la ronda es
    única (ronda 1) y se fija en la vista.
    """

    rol = forms.IntegerField(label="Rol", min_value=1)
    experto = forms.IntegerField(label="Experto", min_value=1)
    justificacion = forms.CharField(
        label="Justificación", required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, fases=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fases = list(fases)
        for fase in self.fases:
            prefijo = f"fase_{fase.pk}_"
            for nombre, etiqueta in (
                ("optimista", "Optimista (O)"),
                ("moda", "Más probable (M)"),
                ("pesimista", "Pesimista (P)"),
            ):
                self.fields[prefijo + nombre] = forms.DecimalField(
                    label=etiqueta, min_value=0, max_digits=10,
                    decimal_places=4,
                    error_messages={"required": CAMPO_OBLIGATORIO},
                )

    def clean(self):
        datos = super().clean()
        for fase in self.fases:
            prefijo = f"fase_{fase.pk}_"
            o = datos.get(prefijo + "optimista")
            m = datos.get(prefijo + "moda")
            p = datos.get(prefijo + "pesimista")
            if o is not None and m is not None and p is not None:
                if not (o <= m <= p):
                    self.add_error(
                        prefijo + "pesimista",
                        "Debe cumplirse optimista ≤ más probable ≤ "
                        "pesimista.",
                    )
        return datos


class RolForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre del rol", max_length=80,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    nivel = forms.IntegerField(
        label="Nivel", min_value=1,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )


class ExpertoForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre del experto", max_length=150,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )


class ParametroForm(forms.Form):
    CLAVES = (
        ("horas_semana", "Horas por semana"),
        ("semanas_año", "Semanas por año"),
        ("tasa_cargas_patronales", "Tasa de cargas patronales"),
        ("eficiencia", "Eficiencia"),
        ("umbral_dispersion_delphi", "Umbral de dispersión Delphi"),
    )

    clave = forms.ChoiceField(
        label="Parámetro", choices=CLAVES,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    valor = forms.DecimalField(
        label="Valor", max_digits=14, decimal_places=6,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    vigente_desde = _fecha("Vigente desde")
    vigente_hasta = _fecha("Vigente hasta", required=False)
    verificado = forms.BooleanField(
        label="Verificado", required=False,
    )

    def clean(self):
        datos = super().clean()
        desde = datos.get("vigente_desde")
        hasta = datos.get("vigente_hasta")
        if desde and hasta and hasta < desde:
            self.add_error(
                "vigente_hasta",
                "La fecha de fin no puede ser anterior a la de inicio.",
            )
        return datos


class SalarioForm(forms.Form):
    rol = forms.IntegerField(label="Rol", min_value=1)
    salario_bruto = forms.DecimalField(
        label="Salario bruto mensual", max_digits=14,
        decimal_places=2, min_value=0,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    vigente_desde = _fecha("Vigente desde")
    vigente_hasta = _fecha("Vigente hasta", required=False)

    def clean(self):
        datos = super().clean()
        desde = datos.get("vigente_desde")
        hasta = datos.get("vigente_hasta")
        if desde and hasta and hasta < desde:
            self.add_error(
                "vigente_hasta",
                "La fecha de fin no puede ser anterior a la de inicio.",
            )
        return datos


class CostoForm(forms.Form):
    """Costo directo o indirecto de una versión en borrador."""

    concepto = forms.CharField(
        label="Concepto / departamento", max_length=150,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )
    monto = forms.DecimalField(
        label="Monto (USD)", max_digits=14, decimal_places=2,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )


class CostoIndirectoForm(CostoForm):
    concepto = forms.CharField(
        label="Departamento", max_length=80,
        error_messages={"required": CAMPO_OBLIGATORIO},
    )


def a_decimal(valor):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise forms.ValidationError("Ingrese un número válido.") from exc
