from django.core.management.base import BaseCommand, CommandError

from estados_financieros.composition import crear_estados_financieros_service
from estados_financieros.exceptions import EstadosFinancierosError
from estados_financieros.formato import cifra


class Command(BaseCommand):
    help = (
        "Calcula el Balance General y el Estado de Resultados de un período "
        "abierto (CU-07.5, CU-07.6). Un período cerrado no se recalcula."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "periodo", help="Nombre exacto o id del período contable."
        )

    def handle(self, *args, **opciones):
        servicio = crear_estados_financieros_service()
        try:
            _, estados = servicio.generar_por_comando(opciones["periodo"])
        except EstadosFinancierosError as error:
            raise CommandError(str(error)) from error
        for datos in estados.values():
            self.stdout.write(f"\n{datos['titulo']} · {datos['cubre']}")
            for fila in datos["filas"]:
                importe = ("" if fila["importe"] is None
                           else cifra(fila["importe"]))
                self.stdout.write(
                    f"{fila['codigo']:>6}  {fila['texto']:<58}{importe:>16}"
                )
            if "cuadra" in datos:
                self.stdout.write(
                    "Activo = Pasivo + Patrimonio: "
                    + ("cuadra" if datos["cuadra"] else
                       f"no cuadra ({cifra(datos['diferencia'])})")
                )
