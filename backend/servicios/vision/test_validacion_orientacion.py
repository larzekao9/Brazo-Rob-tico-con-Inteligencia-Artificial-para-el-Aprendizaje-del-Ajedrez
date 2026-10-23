"""Comprobación de que la calibración no esté girada 180° respecto del FEN, con un tablero sintético y piezas pintadas como discos."""
import cv2
import numpy as np

from backend.servicios.vision import validacion_orientacion as vo

ESQUINAS = np.array([[150, 100], [750, 100], [750, 650], [150, 650]], dtype=np.float32)
"""a8, h8, h1, a1 del tablero sintético."""
INICIAL = {
    **{f"{c}1": "white-rook" for c in "abcdefgh"}, **{f"{c}2": "white-pawn" for c in "abcdefgh"},
    **{f"{c}7": "black-pawn" for c in "abcdefgh"}, **{f"{c}8": "black-rook" for c in "abcdefgh"},
}


def foto_con_piezas(etiquetas: dict[str, str], esquinas: np.ndarray = ESQUINAS) -> np.ndarray:
    """Damero gris con un disco claro en cada casilla 'white' y uno oscuro en cada 'black', ubicadas según `esquinas`."""
    imagen = np.full((750, 900, 3), 110, dtype=np.uint8)
    (x0, y0), (x1, _), (_, y1) = esquinas[0], esquinas[1], esquinas[2]
    paso_x, paso_y = (x1 - x0) / 8, (y1 - y0) / 8
    for casilla, clase in etiquetas.items():
        columna, fila = "abcdefgh".index(casilla[0]), 8 - int(casilla[1])
        centro = (int(x0 + (columna + 0.5) * paso_x), int(y0 + (fila + 0.5) * paso_y))
        color = (225, 225, 225) if clase.startswith("white") else (35, 35, 35)
        cv2.circle(imagen, centro, 24, color, -1)
    return imagen


def test_girar_casilla_y_esquinas() -> None:
    assert vo.girar_casilla("a1") == "h8" and vo.girar_casilla("e2") == "d7" and vo.girar_casilla("h8") == "a1"
    assert np.array_equal(vo.girar_esquinas(vo.girar_esquinas(ESQUINAS)), ESQUINAS)
    assert np.array_equal(vo.girar_esquinas(ESQUINAS)[3], ESQUINAS[1])  # la nueva a1 es la vieja h8


def test_piezas_donde_dice_el_fen_da_ok() -> None:
    informe = vo.comprobar(foto_con_piezas(INICIAL), ESQUINAS, INICIAL)
    assert informe["estado"] == "ok" and informe["brillo_blancas"] > informe["brillo_negras"]


def test_esquinas_giradas_180_se_detectan() -> None:
    foto = foto_con_piezas(INICIAL)
    informe = vo.comprobar(foto, vo.girar_esquinas(ESQUINAS), INICIAL)
    assert informe["estado"] == "invertida" and "180" in informe["mensaje"]


def test_un_solo_color_no_se_puede_comprobar() -> None:
    solo_blancas = {c: e for c, e in INICIAL.items() if e.startswith("white")}
    assert vo.comprobar(foto_con_piezas(solo_blancas), ESQUINAS, solo_blancas)["estado"] == "sin_datos"


def test_sin_contraste_es_dudosa() -> None:
    gris = np.full((750, 900, 3), 110, dtype=np.uint8)
    assert vo.comprobar(gris, ESQUINAS, INICIAL)["estado"] == "dudosa"
