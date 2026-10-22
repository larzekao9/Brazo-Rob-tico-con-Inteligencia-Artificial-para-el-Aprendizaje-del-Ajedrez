"""Jugada más probable dadas la posición anterior y lo que ven las cámaras.

La app ya sabe cómo estaba el tablero antes de la jugada, así que no hace falta reconocer 32 piezas desde cero: solo hay que decidir cuál de las
posiciones posibles (la de antes, si no se movió nada, o la que resulta de cada jugada legal) explica mejor las probabilidades que da la visión en
cada casilla. Se suman los logaritmos de las probabilidades (un producto de expertos) de cada fuente (ocupación vacía/blanca/negra y, si hay modelo,
las 13 clases de pieza) y gana la de mayor puntaje. Un error de lectura en una o dos casillas no cambia el ganador, y si dos posiciones quedan casi
empatadas no se adivina: se informa que no hay una jugada clara.
"""
from __future__ import annotations

from dataclasses import dataclass

import chess
import numpy as np

from backend.servicios.vision.modelo_piezas import CLASE_VACIA

NOMBRES = [f"{c}{f}" for f in range(8, 0, -1) for c in "abcdefgh"]
"""Orden de las 64 filas de toda lectura: a8, b8 … h1 (el de `dividir_en_casillas`)."""
EPSILON = 1e-3
MARGEN_MINIMO = 2.0
"""Diferencia mínima de puntaje (en logaritmos naturales) entre la mejor posición y la segunda para dar una jugada por clara."""
_NOMBRE_DE_PIEZA = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop", chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}


@dataclass
class Lectura:
    """Lo que ve una fuente de visión: probabilidades `(64, clases)` en el orden de `NOMBRES`, los nombres de sus clases y cuánto pesa."""

    probabilidades: np.ndarray
    clases: list[str]
    peso: float = 1.0


def _clase(pieza: chess.Piece | None, clases: list[str]) -> int:
    """Índice de la clase de `pieza` en una fuente: «vacia»/«blanca»/«negra» (ocupación) o «white-pawn»… (piezas)."""
    if pieza is None:
        return clases.index(CLASE_VACIA)
    if "blanca" in clases:
        return clases.index("blanca" if pieza.color == chess.WHITE else "negra")
    return clases.index(f"{'white' if pieza.color == chess.WHITE else 'black'}-{_NOMBRE_DE_PIEZA[pieza.piece_type]}")


def _puntaje(tablero: chess.Board, logaritmos: list[tuple[np.ndarray, list[str], float]]) -> float:
    total = 0.0
    filas = np.arange(64)
    piezas = [tablero.piece_at(chess.parse_square(nombre)) for nombre in NOMBRES]
    for log_p, clases, peso in logaritmos:
        indices = np.array([_clase(pieza, clases) for pieza in piezas])
        total += peso * float(log_p[filas, indices].sum())
    return total


def evaluar_jugadas(fen_antes: str, lecturas: list[Lectura]) -> list[tuple[float, chess.Move | None]]:
    """Puntaje de «no se movió nada» (`None`) y de cada jugada legal, de mayor a menor."""
    if not lecturas:
        raise ValueError("Hacen falta lecturas de la visión")
    logaritmos = [(np.log(np.asarray(l.probabilidades, dtype=np.float64) + EPSILON), l.clases, l.peso) for l in lecturas]
    tablero = chess.Board(fen_antes)
    resultados = [(_puntaje(tablero, logaritmos), None)]
    for jugada in list(tablero.legal_moves):
        tablero.push(jugada)
        resultados.append((_puntaje(tablero, logaritmos), jugada))
        tablero.pop()
    return sorted(resultados, key=lambda r: r[0], reverse=True)


def detectar_jugada_probable(fen_antes: str, lecturas: list[Lectura], margen_minimo: float = MARGEN_MINIMO) -> dict:
    """La jugada que mejor explica lo visto, con su margen sobre la siguiente opción.

    Returns:
        `{"jugada": SAN | None, "uci": str | None, "margen": float, "motivo": str}`. `jugada` es `None` si lo más probable es que no se movió
        nada, o si la mejor opción no le saca `margen_minimo` a la segunda (`motivo` dice cuál de los dos casos).
    """
    ranking = evaluar_jugadas(fen_antes, lecturas)
    (mejor, jugada), (segundo, _) = ranking[0], ranking[1]
    margen = mejor - segundo
    if jugada is None:
        return {"jugada": None, "uci": None, "margen": margen, "motivo": "No se ve ninguna jugada: el tablero está como antes."}
    if margen < margen_minimo:
        return {"jugada": None, "uci": None, "margen": margen, "motivo": "Hay dos jugadas casi igual de probables: no se puede decidir con seguridad."}
    tablero = chess.Board(fen_antes)
    return {"jugada": tablero.san(jugada), "uci": jugada.uci(), "margen": margen, "motivo": "ok"}
