import chess
import pytest

from backend.servicios.estrategias.estrategia_jugada import EstrategiaModelo, EstrategiaStockfish
from backend.servicios.estrategias.fabrica_estrategias import crear_estrategia_jugada

POSICION_INICIAL = chess.STARTING_FEN


def test_crear_estrategia_jugada_motor_devuelve_estrategia_stockfish() -> None:
    estrategia = crear_estrategia_jugada("motor", nivel=5)
    assert isinstance(estrategia, EstrategiaStockfish)
    assert estrategia.nivel == 5


def test_crear_estrategia_jugada_modelo_devuelve_estrategia_modelo() -> None:
    estrategia = crear_estrategia_jugada("modelo")
    assert isinstance(estrategia, EstrategiaModelo)


def test_crear_estrategia_jugada_tipo_no_soportado_lanza_error() -> None:
    with pytest.raises(ValueError):
        crear_estrategia_jugada("participante")


def test_estrategia_stockfish_decide_una_jugada_legal() -> None:
    estrategia = EstrategiaStockfish(nivel=5)
    tablero = chess.Board(POSICION_INICIAL)
    jugada_san = estrategia.decidir_jugada(POSICION_INICIAL)
    assert tablero.parse_san(jugada_san) in tablero.legal_moves


def test_estrategia_modelo_decide_una_jugada_legal(tmp_path) -> None:
    torch = pytest.importorskip("torch")

    from backend.servicios.aprendizaje.modelo_jugadas import NUM_CLASES, RedPrediccionJugadas

    ruta_checkpoint = tmp_path / "checkpoint_prueba.pt"
    torch.save(
        {"state_dict": RedPrediccionJugadas().state_dict(), "num_clases": NUM_CLASES},
        ruta_checkpoint,
    )

    estrategia = EstrategiaModelo(ruta_checkpoint=ruta_checkpoint)
    tablero = chess.Board(POSICION_INICIAL)
    jugada_san = estrategia.decidir_jugada(POSICION_INICIAL)
    assert tablero.parse_san(jugada_san) in tablero.legal_moves
