import chess
import pytest

from backend.servicios.brazo.planificador_movimiento import Paso, forzar_dama, piezas_retiradas, planificar


def _pasos(fen: str, uci: str) -> list[Paso]:
    tablero = chess.Board(fen)
    return planificar(tablero, tablero.parse_uci(uci))


def test_jugada_simple_es_un_solo_paso() -> None:
    assert _pasos(chess.STARTING_FEN, "e2e4") == [Paso("P", "e2", "e4")]
    assert _pasos(chess.STARTING_FEN, "g1f3") == [Paso("N", "g1", "f3")]


def test_captura_retira_primero_la_capturada_al_cementerio() -> None:
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    assert _pasos(fen, "e4d5") == [Paso("p", "d5", "cementerio:0"), Paso("P", "e4", "d5")]


def test_el_cementerio_sigue_donde_quedo() -> None:
    tablero = chess.Board()
    for uci in ("e2e4", "d7d5", "e4d5"):
        tablero.push_uci(uci)
    assert piezas_retiradas(tablero) == 1
    tablero.push_uci("d8d5")
    assert planificar(tablero, tablero.parse_uci("b1c3")) == [Paso("N", "b1", "c3")]
    tablero.push_uci("b1c3")
    assert planificar(tablero, tablero.parse_uci("d5d2"))[0] == Paso("P", "d2", "cementerio:2")


def test_enroque_mueve_rey_y_torre() -> None:
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    assert _pasos(fen, "e1g1") == [Paso("K", "e1", "g1"), Paso("r", "h1", "f1")]
    assert _pasos(fen, "e1c1") == [Paso("K", "e1", "c1"), Paso("r", "a1", "d1")]
    assert _pasos(fen.replace(" w ", " b "), "e8c8") == [Paso("k", "e8", "c8"), Paso("r", "a8", "d8")]


def test_captura_al_paso_retira_el_peon_de_otra_casilla() -> None:
    fen = "rnbqkbnr/ppp1pppp/8/8/3pP3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 3"
    assert _pasos(fen, "d4e3") == [Paso("P", "e4", "cementerio:0"), Paso("p", "d4", "e3")]


def test_coronacion_retira_el_peon_y_pone_la_dama_de_reserva() -> None:
    # con pocas piezas en el FEN, las que faltan para 32 cuentan como ya retiradas: el peón va a la siguiente casilla libre del cementerio
    assert _pasos("8/P6k/8/8/8/8/8/K7 w - - 0 1", "a7a8q") == [Paso("P", "a7", "cementerio:29"), Paso("q", "reserva:dama_blanca", "a8")]
    assert _pasos("7k/8/8/8/8/8/p7/7K b - - 0 1", "a2a1q")[1] == Paso("q", "reserva:dama_negra", "a1")


def test_coronacion_con_captura_retira_primero_la_capturada() -> None:
    pasos = _pasos("1r5k/P7/8/8/8/8/8/K7 w - - 0 1", "a7b8q")
    assert pasos == [Paso("r", "b8", "cementerio:28"), Paso("P", "a7", "cementerio:29"), Paso("q", "reserva:dama_blanca", "b8")]


def test_solo_corona_a_dama() -> None:
    with pytest.raises(ValueError, match="dama"):
        _pasos("8/P6k/8/8/8/8/8/K7 w - - 0 1", "a7a8n")
    assert forzar_dama(chess.Move.from_uci("a7a8n")) == chess.Move.from_uci("a7a8q")
    assert forzar_dama(chess.Move.from_uci("e2e4")) == chess.Move.from_uci("e2e4")
