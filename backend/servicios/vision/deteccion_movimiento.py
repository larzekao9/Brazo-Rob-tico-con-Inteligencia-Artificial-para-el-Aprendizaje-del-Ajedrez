"""Detecta qué jugada se hizo comparando el tablero de antes y de después de
una foto (HU1, RF11).

No hace falta un modelo nuevo para esto: alcanza con probar, entre todas las
jugadas legales de la posición "antes", cuál termina exactamente en la
ubicación de piezas de la posición "después". Es la forma estándar de
resolver esto en ajedrez por cámara — más simple y más confiable que tratar
de leer la jugada directamente de la imagen.
"""
from __future__ import annotations

import chess


def detectar_jugada(fen_antes: str, fen_despues: str) -> str | None:
    """Encuentra la jugada legal que lleva de `fen_antes` a `fen_despues`.

    Solo compara la ubicación de piezas (primer campo del FEN) — el turno,
    el enroque y el al paso no se pueden leer de forma confiable de una
    foto (ver `reconocimiento.py`), así que no se usan para decidir.

    Args:
        fen_antes: FEN reconocido antes de la jugada (el turno importa acá:
            determina de quién son las jugadas legales a probar).
        fen_despues: FEN reconocido después de la jugada.

    Returns:
        La jugada encontrada, en notación SAN, o `None` si ninguna jugada
        legal explica la diferencia (ruido de reconocimiento, o no hubo
        ninguna jugada entre las dos fotos).
    """
    tablero = chess.Board(fen_antes)
    piezas_despues = fen_despues.split(" ")[0]

    for jugada in list(tablero.legal_moves):
        jugada_san = tablero.san(jugada)
        tablero.push(jugada)
        coincide = tablero.fen().split(" ")[0] == piezas_despues
        tablero.pop()
        if coincide:
            return jugada_san
    return None
