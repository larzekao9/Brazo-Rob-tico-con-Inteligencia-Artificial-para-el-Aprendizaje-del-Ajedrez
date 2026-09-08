import chess

from backend.servicios.vision.deteccion_movimiento import detectar_jugada

POSICION_INICIAL = chess.STARTING_FEN


def test_detectar_jugada_reconoce_una_apertura_simple() -> None:
    fen_despues = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    assert detectar_jugada(POSICION_INICIAL, fen_despues) == "e4"


def test_detectar_jugada_reconoce_una_captura() -> None:
    # Posición tras 1.e4 e5 2.Nf3 Nc6, antes/después de que blancas jueguen 3.Nxe5.
    fen_antes = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    fen_despues = "r1bqkbnr/pppp1ppp/2n5/4N3/4P3/8/PPPP1PPP/RNBQKB1R b KQkq - 0 3"
    assert detectar_jugada(fen_antes, fen_despues) == "Nxe5"


def test_detectar_jugada_sin_diferencia_valida_devuelve_none() -> None:
    fen_al_azar = "8/8/8/8/8/8/8/K6k w - - 0 1"
    assert detectar_jugada(POSICION_INICIAL, fen_al_azar) is None
