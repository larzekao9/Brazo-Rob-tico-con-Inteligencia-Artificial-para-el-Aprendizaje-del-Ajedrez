import chess
import pytest

from backend.engine import analizar_posicion, calcular_jugada, obtener_variaciones

POSICION_INICIAL = chess.STARTING_FEN
# Mate en 1 para las blancas: Damas en h5, torre puede dar mate.
MATE_EN_UNO = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 3"


@pytest.mark.parametrize(
    "fen",
    [
        POSICION_INICIAL,
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # 1.e4 e5
        "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # 1.e4 c5 (Siciliana)
    ],
)
def test_calcular_jugada_devuelve_jugada_legal(fen: str) -> None:
    tablero = chess.Board(fen)
    jugada_san = calcular_jugada(fen, nivel=5, tiempo_limite=0.2)
    assert tablero.parse_san(jugada_san) in tablero.legal_moves


def test_calcular_jugada_encuentra_mate_en_uno() -> None:
    jugada_san = calcular_jugada(MATE_EN_UNO, nivel=20, tiempo_limite=0.5)
    assert jugada_san == "Qxf7#"


def test_calcular_jugada_valida_nivel() -> None:
    with pytest.raises(ValueError):
        calcular_jugada(POSICION_INICIAL, nivel=21)


def test_analizar_posicion_detecta_mate_forzado() -> None:
    resultado = analizar_posicion(MATE_EN_UNO, nivel=20, tiempo_limite=0.5)
    assert resultado["mate_en"] == 1
    assert resultado["jugada"] == "Qxf7#"


def test_obtener_variaciones_devuelve_multiples_jugadas() -> None:
    variaciones = obtener_variaciones(POSICION_INICIAL, nivel=10, num_variaciones=3, tiempo_limite=0.2)
    assert len(variaciones) == 3
    tablero = chess.Board(POSICION_INICIAL)
    for jugada_san in variaciones:
        assert tablero.parse_san(jugada_san) in tablero.legal_moves
