from django import forms

from .models import TipoProducto

MAXIMO = 10 ** 10


class EventoSteamForm(forms.Form):
    """Formato del evento que envía el servicio Steam simulado."""

    id = forms.RegexField(regex=r"^[A-Za-z0-9_-]{4,64}$")
    titulo = forms.CharField(max_length=120)
    tipo = forms.ChoiceField(choices=TipoProducto.choices)
    cantidad = forms.IntegerField(min_value=1, max_value=10000)
    precio_unitario = forms.DecimalField(
        min_value=0.01, max_value=MAXIMO, decimal_places=2
    )
    moneda = forms.RegexField(regex=r"^[A-Za-z]{3}$")
    pais = forms.RegexField(regex=r"^[A-Za-z]{2}$")
    fecha_hora = forms.DateTimeField()
    comision = forms.DecimalField(min_value=0, max_value=MAXIMO,
                                  decimal_places=2)
    impuesto = forms.DecimalField(min_value=0, max_value=MAXIMO,
                                  decimal_places=2, required=False)

    def datos_servicio(self):
        datos = self.cleaned_data
        return {
            "identificador": datos["id"], "titulo": datos["titulo"].strip(),
            "tipo_producto": datos["tipo"], "cantidad": datos["cantidad"],
            "precio_unitario": datos["precio_unitario"],
            "moneda": datos["moneda"], "pais": datos["pais"],
            "fecha_hora": datos["fecha_hora"], "comision": datos["comision"],
            "impuesto": datos["impuesto"] or 0,
        }


class FiltroVentasForm(forms.Form):
    q = forms.CharField(required=False, max_length=120)
    desde = forms.DateField(required=False)
    hasta = forms.DateField(required=False)
