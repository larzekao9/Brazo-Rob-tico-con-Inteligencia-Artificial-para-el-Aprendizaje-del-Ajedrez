import chess
import pytest

from backend.servicios.estrategias.estrategia_jugada import EstrategiaStockfish
from backend.servicios.estrategias.fabrica_estrategias import crear_estrategia_jugada

POSICION_INICIAL = chess.STARTING_FEN


def test_crear_estrategia_jugada_motor_devuelve_estrategia_stockfish() -> None:
    estrategia = crear_estrategia_jugada("motor", nivel=5)
    assert isinstance(estrategia, EstrategiaStockfish)
    assert estrategia.nivel == 5


def test_crear_estrategia_jugada_tipo_no_soportado_lanza_error() -> None:
    with pytest.raises(ValueError):
        crear_estrategia_jugada("modelo")


def test_estrategia_stockfish_decide_una_jugada_legal() -> None:
    estrategia = EstrategiaStockfish(nivel=5)
    tablero = chess.Board(POSICION_INICIAL)
    jugada_san = estrategia.decidir_jugada(POSICION_INICIAL)
    assert tablero.parse_san(jugada_san) in tablero.legal_moves
