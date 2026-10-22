import chess
import numpy as np

from backend.servicios.vision.jugada_probable import NOMBRES, Lectura, detectar_jugada_probable, evaluar_jugadas

INICIAL = chess.STARTING_FEN
OCUPACION = ["vacia", "blanca", "negra"]
PIEZAS = ["black-bishop", "black-king", "black-knight", "black-pawn", "black-queen", "black-rook", "vacia",
          "white-bishop", "white-king", "white-knight", "white-pawn", "white-queen", "white-rook"]
NOMBRE = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop", chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}


def _lectura_de(tablero: chess.Board, clases: list[str], seguridad: float = 0.9, peso: float = 1.0) -> Lectura:
    """Lo que vería una visión perfecta (con `seguridad` de acierto) sobre `tablero`."""
    probs = np.full((64, len(clases)), (1 - seguridad) / (len(clases) - 1))
    for i, nombre in enumerate(NOMBRES):
        pieza = tablero.piece_at(chess.parse_square(nombre))
        if pieza is None:
            clase = "vacia"
        elif "blanca" in clases:
            clase = "blanca" if pieza.color == chess.WHITE else "negra"
        else:
            clase = f"{'white' if pieza.color == chess.WHITE else 'black'}-{NOMBRE[pieza.piece_type]}"
        probs[i, clases.index(clase)] = seguridad
    return Lectura(probs, clases, peso)


def _tras(fen: str, uci: str) -> chess.Board:
    tablero = chess.Board(fen)
    tablero.push_uci(uci)
    return tablero


def test_detecta_la_jugada_con_ocupacion_y_con_piezas() -> None:
    visto = _tras(INICIAL, "e2e4")
    assert detectar_jugada_probable(INICIAL, [_lectura_de(visto, OCUPACION)])["jugada"] == "e4"
    assert detectar_jugada_probable(INICIAL, [_lectura_de(visto, OCUPACION), _lectura_de(visto, PIEZAS, peso=0.5)])["jugada"] == "e4"


def test_el_tipo_de_pieza_desempata_lo_que_la_ocupacion_no_ve() -> None:
    fen = "8/P6k/8/8/8/8/8/4K3 w - - 0 1"
    visto = _tras(fen, "a7a8n")  # corona a caballo: por ocupación es igual que a dama
    assert detectar_jugada_probable(fen, [_lectura_de(visto, PIEZAS)])["jugada"] == "a8=N"


def test_tolera_errores_de_lectura_en_varias_casillas() -> None:
    lectura = _lectura_de(_tras(INICIAL, "g1f3"), OCUPACION)
    for casilla in ("a3", "d5", "h6"):  # tres casillas mal vistas, lejos de la jugada
        fila = NOMBRES.index(casilla)
        lectura.probabilidades[fila] = [0.1, 0.8, 0.1]
    assert detectar_jugada_probable(INICIAL, [lectura])["jugada"] == "Nf3"


def test_sin_cambios_no_hay_jugada_y_el_empate_no_se_adivina() -> None:
    antes = chess.Board(INICIAL)
    r = detectar_jugada_probable(INICIAL, [_lectura_de(antes, OCUPACION)])
    assert r["jugada"] is None and "como antes" in r["motivo"]
    incierta = Lectura(np.full((64, 3), 1 / 3), OCUPACION)
    assert detectar_jugada_probable(INICIAL, [incierta])["jugada"] is None


def test_captura_y_enroque_salen_por_la_posicion_resultante() -> None:
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    assert detectar_jugada_probable(fen, [_lectura_de(_tras(fen, "e1g1"), PIEZAS)])["jugada"] == "O-O"
    fen = "4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1"
    assert detectar_jugada_probable(fen, [_lectura_de(_tras(fen, "e4d5"), OCUPACION)])["jugada"] == "exd5"


def test_el_ranking_pone_primero_la_jugada_real() -> None:
    ranking = evaluar_jugadas(INICIAL, [_lectura_de(_tras(INICIAL, "d2d4"), OCUPACION)])
    assert ranking[0][1].uci() == "d2d4" and len(ranking) == 21  # 20 jugadas + "no se movió"


def test_jugada_clara_trae_estado_confirmada_y_alternativas_ordenadas() -> None:
    resultado = detectar_jugada_probable(INICIAL, [_lectura_de(_tras(INICIAL, "e2e4"), OCUPACION)])

    assert resultado["estado"] == "confirmada" and resultado["uci"] == "e2e4"
    assert resultado["alternativas"][0] == {"uci": "e2e4", "san": "e4", "puntaje": 0.0}
    assert all(a["puntaje"] < 0 for a in resultado["alternativas"][1:])


def test_sin_cambio_en_el_tablero_no_es_una_jugada() -> None:
    resultado = detectar_jugada_probable(INICIAL, [_lectura_de(chess.Board(INICIAL), OCUPACION)])

    assert resultado["estado"] == "sin_cambio" and resultado["jugada"] is None
    assert resultado["alternativas"][0]["uci"] is None


def test_lectura_poco_segura_queda_dudosa_y_ofrece_la_mas_probable_como_alternativa() -> None:
    resultado = detectar_jugada_probable(INICIAL, [_lectura_de(_tras(INICIAL, "e2e4"), OCUPACION, seguridad=0.4)])

    assert resultado["estado"] == "dudosa" and resultado["jugada"] is None
    assert "e2e4" in [a["uci"] for a in resultado["alternativas"]]


def test_coronacion_sin_tipo_de_pieza_asume_dama_y_lo_avisa() -> None:
    fen = "8/P6k/8/8/8/8/8/4K3 w - - 0 1"
    resultado = detectar_jugada_probable(fen, [_lectura_de(_tras(fen, "a7a8q"), OCUPACION)])

    assert resultado["estado"] == "confirmada" and resultado["jugada"] == "a8=Q" and resultado["coronacion_asumida"] is True


def test_coronacion_con_modelo_de_piezas_no_necesita_asumir_nada() -> None:
    fen = "8/P6k/8/8/8/8/8/4K3 w - - 0 1"
    visto = _tras(fen, "a7a8n")
    resultado = detectar_jugada_probable(fen, [_lectura_de(visto, OCUPACION), _lectura_de(visto, PIEZAS, seguridad=0.95)])

    assert resultado["jugada"] == "a8=N" and resultado["coronacion_asumida"] is False
