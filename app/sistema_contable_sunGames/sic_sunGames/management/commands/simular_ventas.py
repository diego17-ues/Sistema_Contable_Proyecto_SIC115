"""Ejecuta un ciclo de venta simulada o mantiene el scheduler activo."""

import json
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from simulador_steam.ciclos import ejecutar_ciclo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta el simulador Steam una vez o cada intervalo configurado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--continuo", action="store_true",
            help="repite el ciclo según SIMULATOR_INTERVAL_SECONDS",
        )

    def handle(self, *args, **options):
        intervalo = int(getattr(settings, "SIMULATOR_INTERVAL_SECONDS", 300))
        if intervalo < 1:
            raise CommandError("SIMULATOR_INTERVAL_SECONDS debe ser mayor a 0.")

        if not options["continuo"]:
            self._ejecutar_y_mostrar()
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduler de ventas activo; intervalo: {intervalo} segundos."
            )
        )
        while True:
            try:
                self._ejecutar_y_mostrar()
            except Exception:
                logger.exception("El ciclo de Steam falló; continúa el scheduler.")
            time.sleep(intervalo)

    def _ejecutar_y_mostrar(self):
        resultado = ejecutar_ciclo()
        self.stdout.write(json.dumps(resultado, ensure_ascii=False))
