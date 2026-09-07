"""Tests del armado de FEN a partir de la ocupación por casilla.

No dependen del dataset ni de un checkpoint entrenado — solo prueban la
lógica de `_ocupacion_a_fen_piezas` / `_letra_fen` con datos inventados.
"""
from __future__ import annotations

import chess

from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.reconocimiento import _letra_fen, _ocupacion_a_fen_piezas

POSICION_INICIAL_FEN_PIEZAS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"


def _ocupacion_posicion_inicial() -> dict[str, str]:
    """Arma el dict de ocupación (casilla -> etiqueta) de la posición inicial."""
    orden_piezas = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"]
    ocupacion: dict[str, str] = {}
    for columna, tipo in zip("abcdefgh", orden_piezas):
        ocupacion[f"{columna}8"] = f"black-{tipo}"
        ocupacion[f"{columna}7"] = "black-pawn"
        ocupacion[f"{columna}2"] = "white-pawn"
        ocupacion[f"{columna}1"] = f"white-{tipo}"
    for fila in range(3, 7):
        for columna in "abcdefgh":
            ocupacion[f"{columna}{fila}"] = CLASE_VACIA
    return ocupacion


def test_letra_fen_mayuscula_para_blancas_minuscula_para_negras() -> None:
    assert _letra_fen("white-knight") == "N"
    assert _letra_fen("black-knight") == "n"
    assert _letra_fen("white-king") == "K"
    assert _letra_fen("black-pawn") == "p"


def test_ocupacion_a_fen_piezas_reconoce_la_posicion_inicial() -> None:
    fen_piezas = _ocupacion_a_fen_piezas(_ocupacion_posicion_inicial())
    assert fen_piezas == POSICION_INICIAL_FEN_PIEZAS


def test_fen_de_posicion_inicial_es_valido_para_python_chess() -> None:
    fen_piezas = _ocupacion_a_fen_piezas(_ocupacion_posicion_inicial())
    tablero = chess.Board(f"{fen_piezas} w - - 0 1")
    assert tablero.fen().startswith(POSICION_INICIAL_FEN_PIEZAS)


def test_ocupacion_a_fen_piezas_tablero_vacio() -> None:
    ocupacion = {f"{col}{fila}": CLASE_VACIA for col in "abcdefgh" for fila in range(1, 9)}
    assert _ocupacion_a_fen_piezas(ocupacion) == "8/8/8/8/8/8/8/8"
