"""Servicio Steam simulado (CU-08.4). No es una conexión real con Steam.

Programa independiente (solo biblioteca estándar) que envía eventos de venta
al sistema contable, uno por cada venta "realizada".

Uso, con el servidor en marcha y el mismo token que STEAM_WEBHOOK_TOKEN:

    python simulador_steam/simulador.py --token <token>            # continuo
    python simulador_steam/simulador.py --token <token> --ventas 3 # 3 ventas
    python simulador_steam/simulador.py --intervalo 10 \
        --url http://127.0.0.1:8000

El token también se puede leer de la variable de entorno STEAM_WEBHOOK_TOKEN.
"""

import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from urllib import error, request

CATALOGO = (
    ("Título A", "JUEGO", Decimal("19.99")),
    ("Título B", "JUEGO", Decimal("14.99")),
    ("Título C", "JUEGO", Decimal("9.99")),
    ("Título A · Pack de niveles", "DLC", Decimal("4.99")),
    ("Título B · Banda sonora", "DLC", Decimal("2.99")),
)
PAISES = ("SV", "US", "MX", "GT", "ES", "BR")
COMISION = Decimal("0.30")
CENTAVO = Decimal("0.01")


def generar_evento(azar=random):
    titulo, tipo, precio = azar.choice(CATALOGO)
    cantidad = azar.randint(1, 5)
    total = precio * cantidad
    return {
        "id": f"STM-{uuid.uuid4().hex[:12].upper()}",
        "titulo": titulo,
        "tipo": tipo,
        "cantidad": cantidad,
        "precio_unitario": str(precio),
        "moneda": "USD",
        "pais": azar.choice(PAISES),
        "fecha_hora": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comision": str((total * COMISION).quantize(CENTAVO, ROUND_HALF_UP)),
        "impuesto": "0.00",
    }


def enviar(url, token, datos=None):
    cuerpo = json.dumps(datos or {}).encode()
    peticion = request.Request(url, data=cuerpo, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    })
    try:
        with request.urlopen(peticion, timeout=10) as respuesta:
            return respuesta.status, json.loads(respuesta.read() or b"{}")
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=os.getenv("STEAM_WEBHOOK_TOKEN"))
    parser.add_argument("--intervalo", type=float, default=30,
                        help="segundos entre ventas (por defecto 30)")
    parser.add_argument("--ventas", type=int, default=0,
                        help="cantidad de ventas a enviar; 0 = sin límite")
    opciones = parser.parse_args(argv)
    if not opciones.token:
        parser.error("indica --token o la variable STEAM_WEBHOOK_TOKEN")
    base = opciones.url.rstrip("/")
    enviadas = 0
    try:
        while not opciones.ventas or enviadas < opciones.ventas:
            enviar(f"{base}/api/steam/latido/", opciones.token)
            evento = generar_evento()
            estado, respuesta = enviar(f"{base}/api/steam/ventas/",
                                       opciones.token, evento)
            print(f"{evento['id']} {evento['titulo']} x{evento['cantidad']} "
                  f"-> {estado} {respuesta}")
            enviadas += 1
            if not opciones.ventas or enviadas < opciones.ventas:
                time.sleep(opciones.intervalo)
    except (error.URLError, KeyboardInterrupt) as exc:
        print(f"Simulador detenido: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
