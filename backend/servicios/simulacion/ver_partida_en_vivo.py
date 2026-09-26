"""Ventana PyBullet aparte que refleja en vivo el tablero de una partida real.

Uso:
    python -m backend.servicios.simulacion.ver_partida_en_vivo [partida_id] [token]

Si no se pasa `partida_id`, usa la partida más reciente sin terminar de
`GET /partida`. `token` es el access token de `POST /auth/login`
(`GET /partida/{id}` lo exige vía `Authorization: Bearer <token>`).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

import chess
import pybullet as p

from backend.servicios.simulacion.escena import (
    cargar_formas_visuales_piezas,
    cerrar_escena,
    crear_escena,
    sincronizar_piezas,
)

BACKEND_URL = os.environ.get("AJEDREZ_BACKEND_URL", "http://localhost:8000")
INTERVALO_POLL_SEGUNDOS = 1.0


def _pedir_json(ruta: str, token: str | None = None) -> object:
    encabezados = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(f"{BACKEND_URL}{ruta}", headers=encabezados)
    with urllib.request.urlopen(request, timeout=5) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def _elegir_id_mas_reciente_sin_terminar(partidas: list[dict]) -> str:
    sin_terminar = [partida for partida in partidas if not partida["terminada"]]
    if not sin_terminar:
        raise SystemExit(
            "No hay partidas sin terminar en el backend. Pasá un partida_id explícito:\n"
            "python -m backend.servicios.simulacion.ver_partida_en_vivo <partida_id> <token>"
        )
    return max(sin_terminar, key=lambda partida: partida["creada_en"])["id"]


def resolver_partida_id(partida_id: str | None) -> str:
    if partida_id is not None:
        return partida_id
    partidas = _pedir_json("/partida")
    elegida = _elegir_id_mas_reciente_sin_terminar(partidas)
    print(f"No se pasó partida_id, usando la más reciente sin terminar: {elegida}")
    return elegida


def obtener_fen(partida_id: str, token: str | None) -> str:
    estado = _pedir_json(f"/partida/{partida_id}", token=token)
    return estado["fen"]


def main() -> None:
    argumentos = sys.argv[1:]
    partida_id_arg = argumentos[0] if len(argumentos) >= 1 else None
    token = argumentos[1] if len(argumentos) >= 2 else None

    try:
        partida_id = resolver_partida_id(partida_id_arg)
    except urllib.error.URLError as error:
        raise SystemExit(f"No se pudo conectar a {BACKEND_URL}: {error}") from error

    if token is None:
        raise SystemExit(
            "GET /partida/{id} requiere autenticación (Authorization: Bearer <token>).\n"
            "Pasalo como segundo argumento:\n"
            f"python -m backend.servicios.simulacion.ver_partida_en_vivo {partida_id} <token>\n"
            "El token se obtiene con POST /auth/login."
        )

    client_id, _casillas, piezas = crear_escena(modo_gui=True)
    formas_visuales = cargar_formas_visuales_piezas(client_id)

    ultimo_fen: str | None = None
    print(f"Mirando la partida {partida_id} en vivo contra {BACKEND_URL} (Ctrl+C para salir)...")
    try:
        while p.isConnected(physicsClientId=client_id):
            try:
                fen_actual = obtener_fen(partida_id, token)
            except urllib.error.HTTPError as error:
                print(f"Error HTTP {error.code} consultando la partida: {error.reason}")
                time.sleep(INTERVALO_POLL_SEGUNDOS)
                continue
            except urllib.error.URLError as error:
                print(f"No se pudo conectar a {BACKEND_URL}: {error.reason}")
                time.sleep(INTERVALO_POLL_SEGUNDOS)
                continue

            if fen_actual != ultimo_fen:
                tablero = chess.Board(fen_actual)
                piezas = sincronizar_piezas(client_id, piezas, tablero, formas_visuales)
                print(f"Jugada detectada, escena actualizada. FEN: {fen_actual}")
                ultimo_fen = fen_actual

            time.sleep(INTERVALO_POLL_SEGUNDOS)
    except KeyboardInterrupt:
        print("Interrumpido por el usuario.")
    finally:
        if p.isConnected(physicsClientId=client_id):
            cerrar_escena(client_id)


if __name__ == "__main__":
    main()
