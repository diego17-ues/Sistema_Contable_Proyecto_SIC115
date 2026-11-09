from django.contrib import admin

from .models import PeriodoContable


@admin.register(PeriodoContable)
class PeriodoContableAdmin(admin.ModelAdmin):
    """El estado solo cambia con el cierre y la reapertura (CU-07)."""

    list_display = ("nombre", "fecha_inicio", "fecha_fin", "estado")
    readonly_fields = ("estado",)
