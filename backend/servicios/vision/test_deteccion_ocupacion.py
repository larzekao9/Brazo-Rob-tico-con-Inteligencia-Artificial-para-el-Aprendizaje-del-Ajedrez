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


def test_detectar_casilla_de_pieza_ok_ninguna_y_ambigua() -> None:
    from backend.servicios.vision.captura_estable import detectar_casilla_de_pieza

    vacio = np.zeros((64, 3))
    vacio[:, 0] = 1.0
    una = vacio.copy()
    indice = NOMBRES.index("e4")
    una[indice] = [0.05, 0.9, 0.05]
    assert detectar_casilla_de_pieza(una, "blanca") == ("e4", 0.9, "ok")
    assert detectar_casilla_de_pieza(una, "negra")[2] == "ninguna"
    dos = una.copy()
    dos[NOMBRES.index("e5")] = [0.1, 0.8, 0.1]
    assert detectar_casilla_de_pieza(dos, "blanca")[2] == "ambigua"


def test_una_pieza_inclinada_sobre_la_vecina_se_detecta_en_su_casilla() -> None:
    from backend.servicios.vision.captura_estable import detectar_casilla_de_pieza

    p = np.zeros((64, 3))
    p[:, 0] = 1.0
    p[NOMBRES.index("f2")] = [0.0, 0.99, 0.01]
    p[NOMBRES.index("g2")] = [0.4, 0.58, 0.02]  # la cabeza de la pieza cae sobre g2
    assert detectar_casilla_de_pieza(p, "blanca")[:3:2] == ("f2", "ok")


def test_analizar_camaras_fusiona_las_probabilidades(monkeypatch) -> None:
    import numpy as np

    from backend.servicios.vision import verificacion

    nombres = [f"{c}{f}" for f in range(8, 0, -1) for c in "abcdefgh"]
    clases = ["white-pawn", "white-bishop", "vacia"]

    def lectura(a):  # cada cámara ve la casilla e4 con otra duda
        probs = np.tile([0.0, 0.0, 1.0], (64, 1))
        probs[nombres.index("e4")] = a
        return probs

    por_camara = {"principal": lectura([0.5, 0.45, 0.05]), "secundaria": lectura([0.9, 0.05, 0.05])}
    esquinas = np.array([[150, 80], [750, 40], [780, 620], [120, 660]], dtype=np.float32)
    monkeypatch.setattr(verificacion, "probabilidades_de_camara", lambda img, cam, ocupadas=None: (por_camara[cam], nombres, esquinas, 0.0))
    monkeypatch.setattr(verificacion.piezas, "clases_del_modelo", lambda: clases)
    nombres_clases = clases
    monkeypatch.setattr(verificacion.piezas, "mejores_clases", lambda probs, n=3, clases=None: [
        [(nombres_clases[i], float(f[i])) for i in np.argsort(f)[::-1][:n]] for f in probs])
    imagen = np.full((700, 900, 3), 90, dtype=np.uint8)
    vista, casillas = verificacion.analizar_camaras({"principal": imagen, "secundaria": imagen})
    e4 = next(c for c in casillas if c["casilla"] == "e4")
    assert e4["clase"] == "white-pawn" and e4["acuerdo"] is True and e4["por_camara"] == ["white-pawn", "white-pawn"]
    assert vista.shape[1] == 2 * 800  # las dos vistas, lado a lado


def test_fusionar_probabilidades_sube_el_acuerdo_y_deja_dudoso_el_desacuerdo() -> None:
    from backend.servicios.vision.fusion import casillas_en_desacuerdo, fusionar_probabilidades

    # casilla 0: una cámara ve ocupada la casilla (la cabeza de la pieza vecina) y la otra la ve vacía; casilla 1: las dos ven una pieza.
    camara_1 = np.array([[0.05, 0.9, 0.05], [0.1, 0.8, 0.1]])
    camara_2 = np.array([[0.9, 0.05, 0.05], [0.1, 0.8, 0.1]])
    fusion = fusionar_probabilidades([camara_1, camara_2])
    assert fusion[0].max() < 0.5  # desacuerdo: ninguna clase se impone
    assert fusion[1].argmax() == 1 and fusion[1, 1] > 0.8  # acuerdo: la confianza sube respecto de las lecturas sueltas
    assert np.allclose(fusion.sum(axis=1), 1.0)
    assert casillas_en_desacuerdo([camara_1, camara_2]) == [True, False]
    assert np.allclose(fusionar_probabilidades([camara_1]), camara_1)
