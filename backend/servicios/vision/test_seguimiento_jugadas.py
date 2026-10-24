"""Seguimiento de la partida por diferencias entre imágenes: reglas (qué jugada explica qué casillas) y máquina de estados con tableros sintéticos."""
import chess
import cv2
import numpy as np
import pytest

from backend.servicios.vision import referencia_vacia as rv
from backend.servicios.vision import seguimiento_jugadas as sj
from backend.servicios.vision.test_validacion_orientacion import ESQUINAS

ESQ = np.asarray(ESQUINAS, dtype=np.float32)


def _jugada(fen: str, uci: str) -> tuple[chess.Board, chess.Move]:
    tablero = chess.Board(fen)
    return tablero, chess.Move.from_uci(uci)


# --- reglas ---------------------------------------------------------------------------------------------------------------------------
def test_casillas_de_cada_tipo_de_jugada() -> None:
    assert sj.casillas_de_la_jugada(*_jugada(chess.STARTING_FEN, "e2e4")) == {"e2", "e4"}
    enroque = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    assert sj.casillas_de_la_jugada(*_jugada(enroque, "e1g1")) == {"e1", "g1", "h1", "f1"}
    assert sj.casillas_de_la_jugada(*_jugada(enroque, "e1c1")) == {"e1", "c1", "a1", "d1"}
    assert sj.casillas_de_la_jugada(*_jugada("rnbqkbnr/ppp1pppp/8/8/3pP3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 3", "d4e3")) == {"d4", "e3", "e4"}  # al paso


def test_explica_la_jugada_legal_que_cambia_esas_casillas() -> None:
    assert sj.explicar(chess.STARTING_FEN, frozenset({"e2", "e4"})).san == "e4"
    assert sj.explicar(chess.STARTING_FEN, frozenset({"g1", "f3"})).san == "Nf3"
    assert sj.explicar("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", frozenset({"e1", "g1", "h1", "f1"})).san == "O-O"


def test_una_jugada_ilegal_no_se_explica() -> None:
    assert sj.explicar(chess.STARTING_FEN, frozenset({"e2", "e5"})).jugada is None  # el peón no salta tres casillas
    assert sj.explicar(chess.STARTING_FEN, frozenset({"e7", "e5"})).jugada is None  # le toca a las blancas
    assert sj.explicar(chess.STARTING_FEN, frozenset()).jugada is None


def test_tolera_una_casilla_vista_de_mas_si_una_sola_jugada_queda_cerca() -> None:
    e = sj.explicar(chess.STARTING_FEN, frozenset({"e2", "e4", "a3"}))
    assert e.san == "e4" and e.aproximada


def test_coronacion_toma_la_dama() -> None:
    e = sj.explicar("8/P6k/8/8/8/8/8/K7 w - - 0 1", frozenset({"a7", "a8"}))
    assert e.san == "a8=Q+" or e.san.startswith("a8=Q")


# --- máquina de estados con imágenes ---------------------------------------------------------------------------------------------------
def _frame(fen: str, mano: bool = False, semilla: int = 0) -> np.ndarray:
    """Foto sintética del tablero con las piezas de `fen` (discos blancos y negros), vista con las esquinas `ESQ`."""
    plano = np.zeros((rv.LADO, rv.LADO, 3), np.uint8)
    for fila in range(8):
        for columna in range(8):
            color = (60, 90, 120) if (fila + columna) % 2 else (150, 190, 220)
            cv2.rectangle(plano, (columna * 100, fila * 100), (columna * 100 + 99, fila * 100 + 99), color, -1)
    for casilla, pieza in chess.Board(fen).piece_map().items():
        centro = (chess.square_file(casilla) * 100 + 50, (7 - chess.square_rank(casilla)) * 100 + 50)
        cv2.circle(plano, centro, 30, (235, 235, 235) if pieza.color == chess.WHITE else (25, 25, 25), -1)
    if mano:  # una mano grande tapando varias casillas
        cv2.rectangle(plano, (150, 250), (520, 560), (110, 140, 180), -1)
    destino = np.array([[0, 0], [rv.LADO - 1, 0], [rv.LADO - 1, rv.LADO - 1], [0, rv.LADO - 1]], np.float32)
    foto = cv2.warpPerspective(plano, np.linalg.inv(cv2.getPerspectiveTransform(ESQ, destino)), (900, 750), borderValue=(120, 120, 120))
    ruido = np.random.default_rng(semilla).integers(-2, 3, foto.shape)
    return np.clip(foto.astype(np.int16) + ruido, 0, 255).astype(np.uint8)


def _correr(seg: sj.Seguimiento, cuadros: list[np.ndarray]) -> list[dict]:
    return [seg.actualizar(c) for c in cuadros]


def _posicion_tras(*ucis: str) -> str:
    tablero = chess.Board()
    for uci in ucis:
        tablero.push_uci(uci)
    return tablero.fen()


def test_detecta_la_jugada_cuando_el_tablero_queda_quieto() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio, tras_e4 = chess.STARTING_FEN, _posicion_tras("e2e4")
    res = _correr(seg, [_frame(inicio, semilla=1), _frame(inicio, semilla=2), _frame(inicio, semilla=3),  # foto base y espera
                        _frame(tras_e4, mano=True, semilla=4),  # la mano mueve la pieza: hay movimiento
                        _frame(tras_e4, semilla=5), _frame(tras_e4, semilla=6), _frame(tras_e4, semilla=7), _frame(tras_e4, semilla=8), _frame(tras_e4, semilla=9)])
    estados = [r["estado"] for r in res]
    assert estados[:3] == ["tomando_base", "esperando", "esperando"]
    assert estados[3] == "moviendo"
    assert "jugada" in estados and res[estados.index("jugada")]["jugada"] == "e4"
    assert seg.fen.split(" ")[0] == tras_e4.split(" ")[0] and seg.jugadas == ["e4"]
    assert estados[-1] == "esperando"  # la jugada se avisa una sola vez


def test_sigue_la_partida_jugada_tras_jugada_con_cada_bando() -> None:
    seg = sj.Seguimiento(ESQ)
    posiciones = [chess.STARTING_FEN]
    for uci in ("e2e4", "e7e5", "g1f3", "b8c6"):
        posiciones.append(_posicion_tras(*[m for m in ("e2e4", "e7e5", "g1f3", "b8c6")[: len(posiciones)]]))
    _correr(seg, [_frame(posiciones[0], semilla=1)] * 1 + [_frame(posiciones[0], semilla=2), _frame(posiciones[0], semilla=3)])
    for i, fen in enumerate(posiciones[1:], start=10):
        _correr(seg, [_frame(fen, mano=True, semilla=i), _frame(fen, semilla=i + 20), _frame(fen, semilla=i + 40), _frame(fen, semilla=i + 60)])
    assert seg.jugadas == ["e4", "e5", "Nf3", "Nc6"]


def test_una_jugada_ilegal_da_alerta_y_se_recupera_al_dejar_la_pieza() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    ilegal = chess.Board(inicio); ilegal.set_piece_at(chess.E2, None); ilegal.set_piece_at(chess.E5, chess.Piece(chess.PAWN, chess.WHITE))  # peón e2→e5
    _correr(seg, [_frame(inicio, semilla=1), _frame(inicio, semilla=2), _frame(inicio, semilla=3)])
    res = _correr(seg, [_frame(ilegal.fen(), mano=True, semilla=4), _frame(ilegal.fen(), semilla=5), _frame(ilegal.fen(), semilla=6), _frame(ilegal.fen(), semilla=7)])
    assert res[-1]["estado"] == "invalida" and "e2" in res[-1]["cambiadas"] and "e5" in res[-1]["cambiadas"]
    assert seg.jugadas == [] and seg.fen == inicio
    res = _correr(seg, [_frame(inicio, mano=True, semilla=8), _frame(inicio, semilla=9), _frame(inicio, semilla=10), _frame(inicio, semilla=11), _frame(inicio, semilla=12)])
    assert res[-1]["estado"] == "esperando" and seg.ultima_alerta == ""


def test_un_cambio_de_luz_en_todo_el_tablero_no_es_una_jugada() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    _correr(seg, [_frame(inicio, semilla=1), _frame(inicio, semilla=2), _frame(inicio, semilla=3)])
    mas_claro = [np.clip(_frame(inicio, semilla=s).astype(np.int16) * 1.15 + 12, 0, 255).astype(np.uint8) for s in (4, 5, 6, 7)]
    res = _correr(seg, mas_claro)
    assert res[-1]["estado"] == "esperando" and seg.jugadas == []


def test_fijar_posicion_vuelve_a_tomar_la_foto_base() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio, tras_e4 = chess.STARTING_FEN, _posicion_tras("e2e4")
    _correr(seg, [_frame(inicio, semilla=1), _frame(inicio, semilla=2), _frame(inicio, semilla=3)])
    seg.fijar_posicion(tras_e4)  # p. ej. el robot ya jugó
    res = _correr(seg, [_frame(tras_e4, semilla=4), _frame(tras_e4, semilla=5), _frame(tras_e4, semilla=6)])
    assert seg.base is not None and res[-1]["estado"] == "esperando" and seg.fen == tras_e4
    with pytest.raises(ValueError):
        seg.fijar_posicion("esto no es un fen")


# --- la lógica no se confunde con jugadas a medias, alertas y correcciones -----------------------------------------------------------------
def _quieto(seg: sj.Seguimiento, fen: str, cuadros: int = 4, semilla: int = 100) -> list[dict]:
    return _correr(seg, [_frame(fen, semilla=semilla + i) for i in range(cuadros)])


def _sin(fen: str, *casillas: int) -> str:
    tablero = chess.Board(fen)
    for casilla in casillas:
        tablero.remove_piece_at(casilla)
    return tablero.fen()


def test_la_pieza_capturada_retirada_antes_no_es_una_jugada() -> None:
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    seg = sj.Seguimiento(ESQ, fen)
    _quieto(seg, fen, 3)
    res = _quieto(seg, _sin(fen, chess.D5), 4, 200)  # se saca el peón negro y todavía no se mueve el blanco
    assert res[-1]["estado"] == "incompleta" and seg.jugadas == [] and seg.fen == fen
    tras = chess.Board(fen); tras.push_uci("e4d5")
    res = _correr(seg, [_frame(tras.fen(), mano=True, semilla=300)] + [_frame(tras.fen(), semilla=301 + i) for i in range(4)])
    assert seg.jugadas == ["exd5"] and seg.fen == tras.fen()  # ahora sí, una sola vez


def test_una_pieza_levantada_no_cambia_el_turno_y_al_devolverla_sigue_igual() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    _quieto(seg, inicio, 3)
    res = _quieto(seg, _sin(inicio, chess.G1), 4, 200)  # caballo en la mano
    assert res[-1]["estado"] == "incompleta" and seg.jugadas == []
    res = _correr(seg, [_frame(inicio, mano=True, semilla=300)] + [_frame(inicio, semilla=301 + i) for i in range(4)])
    assert res[-1]["estado"] == "esperando" and seg.fen == inicio and seg.jugadas == [] and res[-1]["turno"] == "blancas"
    # y la jugada de verdad se sigue detectando como jugada de las blancas
    tras = _posicion_tras("e2e4")
    _correr(seg, [_frame(tras, mano=True, semilla=400)] + [_frame(tras, semilla=401 + i) for i in range(4)])
    assert seg.jugadas == ["e4"] and seg.fen.split(" ")[0] == tras.split(" ")[0]


def test_una_pieza_a_medias_mucho_tiempo_acaba_en_alerta() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    _quieto(seg, inicio, 3)
    res = _quieto(seg, _sin(inicio, chess.G1), sj.TICKS_PARCIAL + 3, 200)
    assert res[-1]["estado"] == "invalida" and "g1" in res[-1]["mensaje"]


def test_tras_una_jugada_invalida_devolver_la_pieza_no_salta_el_turno() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    ilegal = chess.Board(inicio); ilegal.set_piece_at(chess.E2, None); ilegal.set_piece_at(chess.E5, chess.Piece(chess.PAWN, chess.WHITE))
    _quieto(seg, inicio, 3)
    res = _correr(seg, [_frame(ilegal.fen(), mano=True, semilla=200)] + [_frame(ilegal.fen(), semilla=201 + i) for i in range(4)])
    assert res[-1]["estado"] == "invalida" and "e2 (debería haber peón blanco)" in res[-1]["mensaje"] and "e5 (debería estar vacía)" in res[-1]["mensaje"]
    # la pieza se levanta, queda un rato en la mano y se devuelve
    en_mano = _sin(ilegal.fen(), chess.E5)
    _correr(seg, [_frame(en_mano, mano=True, semilla=300)] + [_frame(en_mano, semilla=301 + i) for i in range(2)])
    assert seg.jugadas == [] and seg.fen == inicio
    res = _correr(seg, [_frame(inicio, mano=True, semilla=400)] + [_frame(inicio, semilla=401 + i) for i in range(4)])
    assert res[-1]["estado"] == "esperando" and res[-1]["turno"] == "blancas" and seg.fen == inicio
    tras = _posicion_tras("d2d4")
    _correr(seg, [_frame(tras, mano=True, semilla=500)] + [_frame(tras, semilla=501 + i) for i in range(4)])
    assert seg.jugadas == ["d4"]  # sigue siendo el turno de las blancas


def test_avisa_si_se_movio_una_pieza_del_bando_que_no_juega() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    _quieto(seg, inicio, 3)
    negra = chess.Board(inicio); negra.push_uci("e2e4"); negra.turn = chess.BLACK
    movida = chess.Board(inicio); movida.set_piece_at(chess.E7, None); movida.set_piece_at(chess.E5, chess.Piece(chess.PAWN, chess.BLACK))
    res = _correr(seg, [_frame(movida.fen(), mano=True, semilla=200)] + [_frame(movida.fen(), semilla=201 + i) for i in range(4)])
    assert res[-1]["estado"] == "invalida" and "e5" in res[-1]["mensaje"] and "negras" in res[-1]["mensaje"] and "le toca a las blancas" in res[-1]["mensaje"]


def test_la_base_sigue_a_un_cambio_de_luz_lento() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio = chess.STARTING_FEN
    _quieto(seg, inicio, 3)
    for paso in range(1, 6):  # la luz sube de a poco: cada paso, quieto, sin que parezca una jugada
        mas_claro = [np.clip(_frame(inicio, semilla=paso * 10 + i).astype(np.int16) * (1 + 0.04 * paso) + 3 * paso, 0, 255).astype(np.uint8) for i in range(3)]
        res = _correr(seg, mas_claro)
        assert res[-1]["estado"] == "esperando"
    assert seg.jugadas == []


def test_deshacer_quita_la_ultima_jugada_y_vuelve_a_tomar_la_base() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio, tras = chess.STARTING_FEN, _posicion_tras("e2e4")
    _quieto(seg, inicio, 3)
    _correr(seg, [_frame(tras, mano=True, semilla=200)] + [_frame(tras, semilla=201 + i) for i in range(3)])
    assert seg.jugadas == ["e4"]
    assert seg.deshacer() == "e4" and seg.fen == inicio and seg.jugadas == [] and seg.base is None
    with pytest.raises(ValueError):
        seg.deshacer()


def test_la_vista_muestra_antes_despues_y_las_candidatas_de_la_jugada() -> None:
    seg = sj.Seguimiento(ESQ)
    inicio, tras = chess.STARTING_FEN, _posicion_tras("e2e4")
    assert seg.vista() == {"disponible": False}
    _quieto(seg, inicio, 3)
    _correr(seg, [_frame(tras, mano=True, semilla=200)] + [_frame(tras, semilla=201 + i) for i in range(3)])
    vista = seg.vista()
    assert vista["disponible"] and vista["jugada"] == "e4" and vista["estado"] == "jugada" and vista["legales"] == 20
    assert {"e2", "e4"} <= set(vista["cambiadas"]) and vista["candidatas"][0]["san"] == "e4" and vista["candidatas"][0]["valida"]
    for clave in ("base", "actual", "diferencia"):
        assert vista[clave].startswith("data:image/jpeg;base64,")
    _quieto(seg, tras, 3, 300)
    assert seg.vista()["jugada"] == "e4"  # la jugada sigue a la vista mientras nada se mueva
    _correr(seg, [_frame(tras, mano=True, semilla=400)])
    assert seg.vista()["cambiadas"] == [] and seg.vista()["entre_cuadros"]  # en cuanto algo se mueve, se muestra lo nuevo


def test_explicar_pide_origen_y_destino() -> None:
    assert sj.explicar(chess.STARTING_FEN, frozenset({"e4"})).jugada is None  # solo el destino
    parcial = sj.explicar(chess.STARTING_FEN, frozenset({"e2"}))
    assert parcial.jugada is None and parcial.parcial and parcial.faltan == {"e3", "e4"}
    assert sj.explicar(chess.STARTING_FEN, frozenset({"e2", "e4"}), puntajes=None).aproximada is False
