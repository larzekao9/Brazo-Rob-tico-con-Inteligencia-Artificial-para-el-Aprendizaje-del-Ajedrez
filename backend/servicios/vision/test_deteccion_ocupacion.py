import chess
import numpy as np

from backend.servicios.vision.captura_estable import NOMBRES, votar
from backend.servicios.vision.deteccion_movimiento import detectar_jugada_por_ocupacion, ocupacion_de_tablero
from backend.servicios.vision.ocupacion import CLASES_OCUPACION

INICIAL = chess.STARTING_FEN


def _despues(fen: str, uci: str) -> dict[str, str]:
    tablero = chess.Board(fen)
    tablero.push_uci(uci)
    return ocupacion_de_tablero(tablero)


def test_detecta_jugada_simple_y_captura() -> None:
    assert detectar_jugada_por_ocupacion(INICIAL, _despues(INICIAL, "e2e4")) == "e4"
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    assert detectar_jugada_por_ocupacion(fen, _despues(fen, "e4d5")) == "exd5"


def test_detecta_enroque_y_al_paso() -> None:
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    assert detectar_jugada_por_ocupacion(fen, _despues(fen, "e1g1")) == "O-O"
    fen = "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"
    assert detectar_jugada_por_ocupacion(fen, _despues(fen, "e5d6")) == "exd6"


def test_tolera_una_casilla_mal_vista_pero_no_adivina_si_empata() -> None:
    observada = _despues(INICIAL, "g1f3")
    observada["a3"] = "blanca"  # ruido en una casilla ajena
    assert detectar_jugada_por_ocupacion(INICIAL, observada) == "Nf3"
    sin_mover = ocupacion_de_tablero(chess.Board(INICIAL))
    assert detectar_jugada_por_ocupacion(INICIAL, sin_mover) is None


def test_coronacion_elige_dama() -> None:
    fen = "8/P6k/8/8/8/8/8/4K3 w - - 0 1"
    assert detectar_jugada_por_ocupacion(fen, _despues(fen, "a7a8q")) == "a8=Q"


def test_votar_ignora_un_cuadro_malo() -> None:
    buena = np.zeros((64, 3))
    buena[:, 0] = 1.0
    mala = np.zeros((64, 3))
    mala[:, 1] = 1.0  # un cuadro con la mano encima: todo "blanca"
    mapa, acuerdo = votar([buena, buena, mala, buena, buena])
    assert set(mapa) == set(NOMBRES) and all(v == CLASES_OCUPACION[0] for v in mapa.values()) and acuerdo == 0.8
