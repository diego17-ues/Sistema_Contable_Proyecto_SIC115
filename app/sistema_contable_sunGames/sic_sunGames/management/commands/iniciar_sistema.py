"""Arranca el servidor local y el scheduler en un solo comando."""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Inicia la interfaz web y el scheduler del simulador Steam."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bind", default=getattr(
                settings, "SIMULATOR_WEB_BIND", "127.0.0.1:8000"
            ), help="host:puerto del servidor Django",
        )
        parser.add_argument(
            "--railway", action="store_true",
            help="usa Gunicorn y el puerto asignado por Railway",
        )

    def handle(self, *args, **options):
        manage_py = Path(settings.BASE_DIR) / "manage.py"
        entorno = os.environ.copy()
        railway = options["railway"]
        bind = self._bind_railway(entorno) if railway else options["bind"]
        comando_web = self._comando_web(manage_py, bind, railway)
        procesos = []
        detener = threading.Event()
        manejadores_senal = {}

        for nombre_senal in ("SIGINT", "SIGTERM"):
            senal = getattr(signal, nombre_senal, None)
            if senal is not None:
                manejadores_senal[senal] = signal.getsignal(senal)
                signal.signal(senal, lambda *_args: detener.set())

        try:
            if railway:
                Session.objects.all().delete()

            servidor = subprocess.Popen(
                comando_web, cwd=settings.BASE_DIR, env=entorno
            )
            procesos.append(("servidor web", servidor))
            self._esperar_web(servidor, bind, detener)

            scheduler = subprocess.Popen(
                [sys.executable, str(manage_py), "simular_ventas", "--continuo"],
                cwd=settings.BASE_DIR,
                env=entorno,
            )
            procesos.append(("scheduler", scheduler))
            self.stdout.write(self.style.SUCCESS(
                f"Interfaz activa en http://{bind}; scheduler Steam activo."
            ))

            while not detener.wait(0.5):
                for nombre, proceso in procesos:
                    if proceso.poll() is not None:
                        raise CommandError(f"El proceso {nombre} se detuvo.")
        except KeyboardInterrupt:
            detener.set()
        except Exception:
            self._detener_procesos(procesos)
            raise
        finally:
            self.stdout.write("Deteniendo servidor y scheduler...")
            self._detener_procesos(procesos)
            for senal, manejador in manejadores_senal.items():
                signal.signal(senal, manejador)

    @staticmethod
    def _bind_railway(entorno):
        puerto = entorno.get("PORT", "").strip()
        try:
            numero_puerto = int(puerto)
        except (TypeError, ValueError) as error:
            raise CommandError("Railway debe proporcionar un PORT válido.") from error
        if not 1 <= numero_puerto <= 65535:
            raise CommandError("El PORT asignado por Railway está fuera de rango.")
        return f"0.0.0.0:{numero_puerto}"

    @staticmethod
    def _comando_web(manage_py, bind, railway):
        if railway:
            return [
                sys.executable, "-m", "gunicorn",
                "sistema_contable_sunGames.wsgi:application",
                "--bind", bind,
                "--workers", os.getenv("WEB_CONCURRENCY", "2"),
                "--access-logfile", "-",
                "--error-logfile", "-",
                "--capture-output",
            ]
        return [
            sys.executable, str(manage_py), "runserver", bind, "--noreload"
        ]

    @staticmethod
    def _esperar_web(servidor, bind, detener):
        _host, puerto = bind.rsplit(":", 1)
        destino = "127.0.0.1" if _host == "0.0.0.0" else _host
        plazo = time.monotonic() + 30
        while time.monotonic() < plazo and not detener.is_set():
            if servidor.poll() is not None:
                raise CommandError("El servidor web no pudo iniciar.")
            try:
                with socket.create_connection((destino, int(puerto)), timeout=1):
                    return
            except OSError:
                time.sleep(0.25)
        if detener.is_set():
            raise CommandError("El inicio se canceló antes de levantar la web.")
        raise CommandError("El servidor web no abrió el puerto en 30 segundos.")

    @staticmethod
    def _detener_procesos(procesos):
        for _nombre, proceso in procesos:
            if proceso.poll() is None:
                try:
                    proceso.terminate()
                except OSError:
                    pass
        for _nombre, proceso in procesos:
            if proceso.poll() is None:
                try:
                    proceso.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        proceso.kill()
                    except OSError:
                        pass
                    proceso.wait(timeout=5)
