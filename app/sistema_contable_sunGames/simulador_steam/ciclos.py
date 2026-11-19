"""Coordinación del ciclo periódico del simulador Steam existente."""

import logging
import time
from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone

from ventas.composition import token_steam
from ventas.repositories import VentaRepository

from .simulador import enviar, generar_evento

logger = logging.getLogger(__name__)
CLAVE_BLOQUEO_CICLO = 732115004


@contextmanager
def _bloqueo_ciclo():
    """Evita ciclos simultáneos entre el scheduler y los workers web."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_try_advisory_lock(%s)", [CLAVE_BLOQUEO_CICLO]
        )
        adquirido = cursor.fetchone()[0]
    try:
        yield adquirido
    finally:
        if adquirido:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_unlock(%s)", [CLAVE_BLOQUEO_CICLO]
                )


def _post_reintentable(url, token, datos, timeout, max_reintentos):
    for intento in range(max_reintentos + 1):
        try:
            estado, _respuesta = enviar(
                url, token, datos, timeout=timeout
            )
        except Exception as error_envio:
            if intento < max_reintentos:
                time.sleep(min(2 ** intento, 4))
                continue
            return False, None, str(error_envio)[:300]

        if estado == 409 and datos:
            # El endpoint ya recibió el mismo identificador en un intento
            # anterior; no se genera otro evento para reemplazarlo.
            return True, estado, "evento ya recibido"
        if 200 <= estado < 300:
            return True, estado, ""
        if estado >= 500 and intento < max_reintentos:
            time.sleep(min(2 ** intento, 4))
            continue
        return False, estado, f"HTTP {estado}"
    return False, None, "se agotaron los reintentos"


def _registrar_ciclo(momento, resultado):
    logger.info(
        "Ciclo Steam hora=%s estado=%s enviadas=%s id=%s título=%s "
        "detalle=%s",
        momento.isoformat(), resultado["estado"], resultado["enviadas"],
        resultado.get("id", "-"), resultado.get("titulo", "-"),
        resultado.get("detalle", "-"),
    )


def ejecutar_ciclo():
    """Genera como máximo una venta y la envía al webhook contable."""
    momento = timezone.now()
    resultado = {"estado": "omitido", "enviadas": 0}
    try:
        with _bloqueo_ciclo() as adquirido:
            if not adquirido:
                resultado["detalle"] = "otro ciclo está en ejecución"
                return _registrar_y_devolver(momento, resultado)

            token = token_steam()
            if not token:
                resultado.update(
                    estado="error", detalle="STEAM_WEBHOOK_TOKEN no está configurado"
                )
                return _registrar_y_devolver(momento, resultado)

            base_url = getattr(
                settings, "SIMULATOR_ACCOUNTING_URL",
                "http://127.0.0.1:8000",
            ).rstrip("/")
            timeout = int(getattr(settings, "SIMULATOR_API_TIMEOUT_SECONDS", 10))
            max_reintentos = int(getattr(settings, "SIMULATOR_MAX_RETRIES", 2))

            _, estado_latido, error_latido = _post_reintentable(
                f"{base_url}/api/steam/latido/", token, {}, timeout,
                max_reintentos,
            )
            if estado_latido is None or error_latido:
                logger.warning(
                    "Falló el latido Steam hora=%s detalle=%s",
                    momento.isoformat(), error_latido or "sin respuesta",
                )

            ventana = int(getattr(
                settings, "SIMULATOR_REAL_SALE_WINDOW_SECONDS", 300
            ))
            ahora_consulta = timezone.now()
            desde = ahora_consulta - timedelta(seconds=ventana)
            if VentaRepository().hubo_venta_real(desde, ahora_consulta):
                resultado["detalle"] = (
                    f"compra real en los últimos {ventana} segundos"
                )
                return _registrar_y_devolver(momento, resultado)

            # La venta es una muestra aleatoria del catálogo del simulador;
            # no depende de que Costos tenga órdenes registradas.
            evento = generar_evento()
            correcto, estado, detalle = _post_reintentable(
                f"{base_url}/api/steam/ventas/", token, evento, timeout,
                max_reintentos,
            )
            if correcto:
                resultado.update(
                    estado="enviada", enviadas=1, id=evento["id"],
                    titulo=evento["titulo"],
                )
            else:
                resultado.update(
                    estado="error", id=evento["id"],
                    titulo=evento["titulo"],
                    detalle=detalle or f"HTTP {estado}",
                )
    except Exception as error_ciclo:
        logger.exception(
            "Falló el ciclo Steam hora=%s", momento.isoformat()
        )
        resultado.update(estado="error", detalle=str(error_ciclo)[:300])
    return _registrar_y_devolver(momento, resultado)


def _registrar_y_devolver(momento, resultado):
    _registrar_ciclo(momento, resultado)
    return resultado
