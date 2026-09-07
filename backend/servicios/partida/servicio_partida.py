"""Orquesta partidas jugables: aplica la jugada humana y responde con la
estrategia de jugada activa.

Las partidas viven en un `RepositorioPartidasEnMemoria` (solo en memoria del
proceso) — alcanza para la demo de estas semanas, no hace falta persistencia
todavía. Quién decide la jugada de respuesta es la estrategia que devuelva
`crear_estrategia_jugada` — hoy siempre Stockfish, mañana también el modelo
propio o un jugador humano, sin tocar este archivo (ver
PLAN_IMPLEMENTACION_COMPLETO.md, secciones 4.1 y 4.3).
"""
from __future__ import annotations

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas, RepositorioPartidasEnMemoria
from backend.servicios.estrategias.fabrica_estrategias import crear_estrategia_jugada

_repositorio: RepositorioPartidas = RepositorioPartidasEnMemoria()


def crear_partida(nivel: int = 20) -> Partida:
    """Crea una partida nueva con el tablero en la posición inicial."""
    partida = Partida(nivel=nivel)
    _repositorio.guardar(partida)
    return partida


def obtener_partida(partida_id: str) -> Partida:
    """Busca una partida por id.

    Raises:
        KeyError: si no existe una partida con ese id.
    """
    return _repositorio.obtener(partida_id)


def mover(partida_id: str, jugada_uci: str) -> dict:
    """Aplica la jugada del humano (UCI) y responde con la jugada de la estrategia activa.

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
        estrategia = crear_estrategia_jugada("motor", nivel=partida.nivel)
        jugada_motor_san = estrategia.decidir_jugada(partida.fen)
        partida.tablero.push_san(jugada_motor_san)

    return {
        "fen": partida.fen,
        "jugada_motor": jugada_motor_san,
        "terminada": partida.terminada,
        "resultado": partida.resultado,
    }
