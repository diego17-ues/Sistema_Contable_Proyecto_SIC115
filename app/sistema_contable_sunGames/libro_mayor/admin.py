from django.contrib import admin

from .models import PeriodoContable

# Ejercicio y períodos (fuente configurable). TODO(CU-07): los cierres
# cambiarán `cerrado` desde su propio caso de uso.
admin.site.register(PeriodoContable)
