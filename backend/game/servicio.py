"""Orquesta partidas jugables: aplica la jugada humana y responde con Stockfish.

Las partidas viven solo en memoria del proceso — alcanza para la demo de estas
3 semanas, no hace falta persistencia todavía.
"""
from __future__ import annotations

from backend.engine.stockfish_wrapper import calcular_jugada
from backend.models.partida import Partida

_partidas: dict[str, Partida] = {}


def crear_partida(nivel: int = 20) -> Partida:
    """Crea una partida nueva con el tablero en la posición inicial."""
    partida = Partida(nivel=nivel)
    _partidas[partida.id] = partida
    return partida


def obtener_partida(partida_id: str) -> Partida:
    """Busca una partida por id.

    Raises:
        KeyError: si no existe una partida con ese id.
    """
    if partida_id not in _partidas:
        raise KeyError(f"No existe una partida con id {partida_id}")
    return _partidas[partida_id]


def mover(partida_id: str, jugada_uci: str) -> dict:
    """Aplica la jugada del humano (UCI) y responde con la jugada de Stockfish.

    Raises:
        KeyError: si no existe una partida con ese id.
        ValueError: si la partida ya terminó o la jugada es inválida/ilegal.
    """
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")

    try:
        jugada_humano = partida.tablero.parse_uci(jugada_uci)
    except ValueError as error:
        raise ValueError(f"Jugada inválida: {jugada_uci}") from error
    partida.tablero.push(jugada_humano)

    jugada_motor_san = None
    if not partida.terminada:
        jugada_motor_san = calcular_jugada(partida.fen, nivel=partida.nivel)
        partida.tablero.push_san(jugada_motor_san)

    return {
        "fen": partida.fen,
        "jugada_motor": jugada_motor_san,
        "terminada": partida.terminada,
        "resultado": partida.resultado,
    }
