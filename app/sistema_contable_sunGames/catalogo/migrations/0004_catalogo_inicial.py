import unicodedata

from django.db import migrations

# Catálogo inicial entregado por el usuario. La naturaleza de cada cuenta
# sale del Manual de aplicación del catálogo («su saldo es deudor/acreedor»,
# «todas las cuentas de egresos tienen saldo deudor»).
NATURALEZAS = (("D", "Deudora"), ("A", "Acreedora"))

RUBROS = {
    "6": "Cuentas de orden y control deudoras",
    "7": "Cuentas de orden y control acreedoras",
}

# Los rubros 3, 5, 6 y 7 no tienen subtipos en el catálogo: sus cuentas usan
# el subtipo 1, que lleva el nombre del rubro.
SUBTIPOS = (
    ("1", "1", "Activo corriente"),
    ("1", "2", "Activo no corriente"),
    ("2", "1", "Pasivo corriente"),
    ("2", "2", "Pasivo no corriente"),
    ("3", "1", "Patrimonio"),
    ("4", "1", "Costos de desarrollo"),
    ("4", "2", "Gastos de administración"),
    ("4", "3", "Gastos de venta"),
    ("4", "4", "Gastos financieros"),
    ("4", "5", "Otros egresos"),
    ("5", "1", "Ingresos"),
    ("6", "1", "Cuentas de orden y control deudoras"),
    ("7", "1", "Cuentas de orden y control acreedoras"),
)

CUENTAS = (
    ("1101", "Caja general", "D"),
    ("1102", "Caja chica", "D"),
    ("1103", "Bancos", "D"),
    ("1104", "Cuentas por cobrar a plataformas", "D"),
    ("1105", "Otras cuentas por cobrar", "D"),
    ("1106", "Videojuegos en desarrollo", "D"),
    ("1107", "Videojuegos terminados", "D"),
    ("1108", "Amortización acumulada de videojuegos", "A"),
    ("1109", "IVA crédito fiscal", "D"),
    ("1110", "Pago a cuenta de impuesto sobre la renta", "D"),
    ("1111", "Anticipos a proveedores", "D"),
    ("1112", "Gastos pagados por anticipado", "D"),
    ("1201", "Mobiliario y equipo de oficina", "D"),
    ("1202", "Equipo de cómputo", "D"),
    ("1203", "Depreciación acumulada", "A"),
    ("1204", "Licencias de software", "D"),
    ("1205", "Amortización acumulada de licencias de software", "A"),
    ("2101", "Proveedores", "A"),
    ("2102", "Acreedores varios", "A"),
    ("2103", "IVA débito fiscal", "A"),
    ("2104", "Retenciones por pagar (ISSS, AFP y renta)", "A"),
    ("2105", "Cargas patronales por pagar", "A"),
    ("2106", "Sueldos y prestaciones por pagar", "A"),
    ("2107", "Impuesto sobre la renta por pagar", "A"),
    ("2108", "Ingresos diferidos", "A"),
    ("2201", "Préstamos bancarios a largo plazo", "A"),
    ("2202", "Préstamos de socios", "A"),
    ("3101", "Capital social", "A"),
    ("3102", "Reserva legal", "A"),
    ("3103", "Utilidades acumuladas", "A"),
    # TODO(CU-06): el manual define 3104 como liquidadora cuyo saldo es la
    # utilidad o la pérdida; se registra acreedora hasta confirmarlo.
    ("3104", "Pérdidas y ganancias", "A"),
    ("4101", "Mano de obra directa de desarrollo", "D"),
    ("4102", "Servicios directos de desarrollo", "D"),
    ("4103", "Costos indirectos de desarrollo", "D"),
    ("4104", "Costo de ventas", "D"),
    ("4201", "Sueldos y salarios administrativos", "D"),
    ("4202", "Prestaciones y cargas patronales", "D"),
    ("4203", "Honorarios profesionales", "D"),
    ("4204", "Alquileres", "D"),
    ("4205", "Servicios básicos", "D"),
    ("4206", "Papelería y útiles", "D"),
    ("4207", "Depreciación de mobiliario y equipo", "D"),
    ("4208", "Amortización de licencias de software", "D"),
    ("4301", "Publicidad y marketing", "D"),
    ("4302", "Comisiones por plataformas", "D"),
    ("4303", "Gastos de lanzamiento", "D"),
    ("4401", "Intereses", "D"),
    ("4402", "Comisiones bancarias", "D"),
    ("4501", "Otros gastos", "D"),
    ("4502", "Gastos por servicios profesionales", "D"),
    ("4503", "Impuesto sobre la renta", "D"),
    ("5101", "Ingresos por licencias de videojuegos", "A"),
    ("5102", "Ingresos por contenido adicional", "A"),
    ("5103", "Descuentos y devoluciones sobre ventas", "D"),
    ("5104", "Ingresos financieros", "A"),
    ("5105", "Otros ingresos", "A"),
    ("6101", "Activos totalmente depreciados o amortizados en uso", "D"),
    ("6102", "Propiedad intelectual registrada", "D"),
    ("6103", "Garantías recibidas", "D"),
    ("6104", "Documentos y valores en custodia", "D"),
    ("7101", "Responsabilidad por activos totalmente depreciados o "
             "amortizados en uso", "A"),
    ("7102", "Responsabilidad por propiedad intelectual registrada", "A"),
    ("7103", "Responsabilidad por garantías recibidas", "A"),
    ("7104", "Responsabilidad por documentos y valores en custodia", "A"),
)


def normalizar(texto):
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(
        c for c in descompuesto if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.casefold().split())


def cargar(apps, schema_editor):
    Rubro = apps.get_model("catalogo", "Rubro")
    Subtipo = apps.get_model("catalogo", "Subtipo")
    Naturaleza = apps.get_model("catalogo", "Naturaleza")
    Cuenta = apps.get_model("catalogo", "Cuenta")
    for codigo, nombre in RUBROS.items():
        Rubro.objects.filter(codigo=codigo).update(nombre=nombre)
    naturalezas = {
        codigo: Naturaleza.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre}
        )[0]
        for codigo, nombre in NATURALEZAS
    }
    subtipos = {}
    for rubro, codigo, nombre in SUBTIPOS:
        subtipos[rubro + codigo] = Subtipo.objects.get_or_create(
            rubro=Rubro.objects.get(codigo=rubro), codigo=codigo,
            defaults={"nombre": nombre},
        )[0]
    for codigo, denominacion, naturaleza in CUENTAS:
        subtipo = subtipos[codigo[:2]]
        Cuenta.objects.get_or_create(
            codigo=codigo,
            defaults={
                "denominacion": denominacion,
                "denominacion_normalizada": normalizar(denominacion),
                "rubro": subtipo.rubro,
                "subtipo": subtipo,
                "naturaleza": naturalezas[naturaleza],
            },
        )


def quitar(apps, schema_editor):
    Cuenta = apps.get_model("catalogo", "Cuenta")
    Cuenta.objects.filter(
        codigo__in=[codigo for codigo, _, _ in CUENTAS],
        aprobaciones__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0003_subtipos_y_naturaleza")]

    operations = [migrations.RunPython(cargar, quitar)]
