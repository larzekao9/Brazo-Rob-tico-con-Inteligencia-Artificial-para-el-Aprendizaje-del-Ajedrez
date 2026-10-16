"""Sesión guiada para juntar fotos etiquetadas de TU tablero y TUS piezas, jugando una partida en el tablero físico.

Cómo se usa: armá la posición inicial en el tablero real y corré

    python -m training.sesion_captura

Cada vez que muevas una pieza en el tablero físico, escribí la jugada en el programa (notación algebraica corta, como `e4`,
`Nf3`, `O-O`, `exd5`). El programa actualiza la posición, te da unos segundos para sacar la mano del tablero, saca la foto con la
cámara fija y guarda las 64 casillas ya etiquetadas en `training/dataset_propio/` (ver `capturar_dataset_propio.py`).

Comandos además de las jugadas:
    fen <piezas>   cargar una posición libre (solo el campo de piezas del FEN), por ejemplo con varias damas para juntar ejemplos
                   de las piezas que menos aparecen; el programa saca la foto de esa posición
    u              deshacer la última jugada (si te equivocaste al escribirla; mové la pieza de vuelta en el tablero físico)
    foto           sacar otra foto de la posición actual (por ejemplo si apareció una mano en la anterior)
    q              terminar y mostrar cuántas muestras hay de cada clase

Consejos para una buena muestra: jugá aperturas y capturas variadas para que cada pieza aparezca en muchas casillas, sacá
siempre la mano del tablero antes de la foto y no muevas ni el tablero ni la cámara. Con 25 a 30 posiciones ya hay más de 1.500
casillas etiquetadas.
"""
from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

import chess
from dotenv import load_dotenv

from training.capturar_dataset_propio import CARPETA_DATASET, capturar_muestras

SEGUNDOS_PARA_SACAR_LA_MANO = 3


def interpretar_orden(tablero: chess.Board, texto: str) -> tuple[chess.Board, str]:
    """Aplica una orden del usuario a la posición y devuelve `(tablero_nuevo, accion)`.

    `accion` es `"foto"` (hay que sacar foto de la nueva posición), `"salir"`, `"nada"` (orden vacía o inválida) o `"error: ..."`.
    No modifica el tablero recibido.
    """
    orden = texto.strip()
    if not orden:
        return tablero, "nada"
    if orden.lower() == "q":
        return tablero, "salir"
    if orden.lower() == "foto":
        return tablero, "foto"
    nuevo = tablero.copy()
    if orden.lower() == "u":
        if not nuevo.move_stack:
            return tablero, "error: no hay jugadas para deshacer"
        nuevo.pop()
        return nuevo, "foto"
    if orden.lower().startswith("fen "):
        try:
            libre = chess.Board(None)
            libre.set_board_fen(orden[4:].strip())
        except ValueError as error:
            return tablero, f"error: FEN de piezas inválido ({error})"
        return libre, "foto"
    try:
        nuevo.push_san(orden)
    except ValueError:
        return tablero, f"error: '{orden}' no es una jugada legal en esta posición"
    return nuevo, "foto"


def resumen_del_dataset(carpeta: Path = CARPETA_DATASET) -> dict[str, int]:
    """Cuántas muestras hay por clase en `carpeta` (cada clase es una subcarpeta)."""
    if not carpeta.exists():
        return {}
    return {sub.name: len(list(sub.glob("*.png"))) for sub in sorted(carpeta.iterdir()) if sub.is_dir()}


def _sacar_foto(tablero: chess.Board) -> None:
    for restantes in range(SEGUNDOS_PARA_SACAR_LA_MANO, 0, -1):
        print(f"  Sacá la mano del tablero... {restantes}", end="\r", flush=True)
        time.sleep(1)
    guardadas = capturar_muestras(tablero.board_fen())
    print(f"  Foto sacada: {guardadas} casillas guardadas.      ")


def main() -> None:
    load_dotenv()
    tablero = chess.Board()
    print(__doc__.split("Cómo se usa:")[0].strip())
    print("\nArmá la posición inicial en el tablero físico y apretá Enter para sacar la primera foto.")
    input()
    _sacar_foto(tablero)
    while True:
        print(f"\nPosición: {tablero.board_fen()}  (juegan {'las blancas' if tablero.turn else 'las negras'})")
        tablero, accion = interpretar_orden(tablero, input("Jugada que hiciste (o fen/u/foto/q): "))
        if accion == "salir":
            break
        if accion == "foto":
            _sacar_foto(tablero)
        elif accion.startswith("error"):
            print(f"  {accion}")
    print("\nMuestras por clase:")
    for clase, cantidad in resumen_del_dataset().items():
        print(f"  {clase:<14} {cantidad}")


if __name__ == "__main__":
    main()
