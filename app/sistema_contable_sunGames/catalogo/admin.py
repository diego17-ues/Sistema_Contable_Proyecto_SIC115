from django.contrib import admin

from .models import Naturaleza, Rubro, Subtipo

# Fuente configurable de rubros, subtipos y naturalezas (CU-06).
# Las cuentas no se registran aquí: solo cambian por CatalogoCuentasService.
admin.site.register(Rubro)
admin.site.register(Subtipo)
admin.site.register(Naturaleza)
