from django.contrib import admin

from .models import Grupo, Naturaleza, Rubro

# Fuente configurable de rubros, naturalezas y grupos válidos (CU-06).
# Las cuentas no se registran aquí: solo cambian por CatalogoCuentasService.
admin.site.register(Rubro)
admin.site.register(Naturaleza)
admin.site.register(Grupo)
