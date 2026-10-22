"""Junta la geometría (`tablero.py`) y la clasificación (`piezas.py`) en un
único `reconocer_tablero(imagen) -> fen` (HU1, PLAN_IMPLEMENTACION_COMPLETO.md
sección 15).

Limitación conocida: una sola foto no dice de quién es el turno, ni si hay
derecho a enroque, ni si hay al paso disponible — esos campos del FEN no se
pueden leer de la imagen. `turno` se recibe como parámetro (lo sabe quien usa
la app, no la foto) y el resto se completa con los valores por defecto más
conservadores ("sin enroque", "sin al paso").
"""
from __future__ import annotations

import numpy as np

from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.piezas import clasificar_pieza, modo_recorte, usa_recorte_ampliado
from backend.servicios.vision.tablero import (
    MARGEN_TABLERO_PORCENTAJE,
    archivo_esquinas,
    cargar_esquinas_calibradas,
    detectar_esquinas_tablero,
    dibujar_grilla_debug,
    dividir_en_casillas,
    enderezar_tablero,
    recortes_ampliados,
)

_LETRA_POR_TIPO = {
    "pawn": "p", "knight": "n", "bishop": "b", "rook": "r", "queen": "q", "king": "k",
}


def _letra_fen(etiqueta_pieza: str) -> str:
    """Convierte una etiqueta del clasificador (ej. "white-knight") a letra FEN ("N")."""
    color, tipo = etiqueta_pieza.split("-")
    letra = _LETRA_POR_TIPO[tipo]
    return letra.upper() if color == "white" else letra


def _ocupacion_a_fen_piezas(ocupacion: dict[str, str]) -> str:
    """Arma el primer campo del FEN (ubicación de piezas) a partir de la ocupación por casilla."""
    filas_fen = []
    for fila in range(8, 0, -1):
        casillas_vacias_seguidas = 0
        fila_fen = ""
        for columna in "abcdefgh":
            etiqueta = ocupacion[f"{columna}{fila}"]
            if etiqueta == CLASE_VACIA:
                casillas_vacias_seguidas += 1
                continue
            if casillas_vacias_seguidas:
                fila_fen += str(casillas_vacias_seguidas)
                casillas_vacias_seguidas = 0
            fila_fen += _letra_fen(etiqueta)
        if casillas_vacias_seguidas:
            fila_fen += str(casillas_vacias_seguidas)
        filas_fen.append(fila_fen)
    return "/".join(filas_fen)


def esquinas_y_margen(imagen: np.ndarray, camara: str = "principal") -> tuple[np.ndarray, float]:
    """Esquinas del tablero y margen de recorte (%) a usar.

    Si la cámara está calibrada (esquinas del área de juego marcadas una vez, ver `tablero.cargar_esquinas_calibradas`) se usan
    esas, con margen 0; si no, se detectan en la foto y se aplica el margen por defecto del borde de madera.
    """
    calibradas = cargar_esquinas_calibradas(archivo_esquinas(camara))
    if calibradas is not None:
        return calibradas, 0.0
    return detectar_esquinas_tablero(imagen), MARGEN_TABLERO_PORCENTAJE


def recortes_de_imagen(imagen: np.ndarray, camara: str = "principal", modo: str | None = None) -> tuple[dict[str, np.ndarray], np.ndarray, float]:
    """Recortes de las 64 casillas que espera el clasificador de piezas cargado, más las esquinas y el margen usados.

    Con la cámara calibrada (margen 0) se usa el recorte con el que se entrenó el modelo (`piezas.modo_recorte`: por volumen 3D o ampliado); si no, el
    recorte justo de cada casilla. Un solo lugar decide, para que entrenamiento, reconocimiento y probador vean lo mismo.
    """
    esquinas, margen = esquinas_y_margen(imagen, camara)
    modo = "justo" if margen else (modo or modo_recorte())
    if modo == "volumen":
        from backend.servicios.vision import geometria3d

        alto, ancho = imagen.shape[:2]
        lente = geometria3d.cargar_lente(camara, ancho, alto)
        return geometria3d.recortes_volumen(imagen, esquinas[::-1], lente), esquinas, margen  # a8,h8,h1,a1 -> a1,h1,h8,a8
    if modo == "ampliado":
        return recortes_ampliados(imagen, esquinas), esquinas, margen
    return dividir_en_casillas(enderezar_tablero(imagen, esquinas), margen), esquinas, margen


def reconocer_tablero(imagen: np.ndarray, turno: str = "w") -> str:
    """Reconoce el tablero de una foto y arma su FEN.

    Args:
        imagen: imagen BGR de un tablero real (la que devuelve `cv2.imread`).
        turno: "w" o "b" — de quién es el turno; no se puede leer de la foto,
            lo indica quien llama (por ejemplo, la interfaz sabe quién acaba
            de mover).

    Returns:
        FEN completo, con enroque y al paso en sus valores por defecto ("-")
        ya que una sola foto no alcanza para determinarlos.

    Raises:
        ValueError: si no se detecta el tablero en la imagen.
    """
    casillas, _, _ = recortes_de_imagen(imagen)
    ocupacion = {nombre: clasificar_pieza(recorte) for nombre, recorte in casillas.items()}
    piezas_fen = _ocupacion_a_fen_piezas(ocupacion)
    return f"{piezas_fen} {turno} - - 0 1"


def generar_imagen_grilla_debug(imagen: np.ndarray, camara: str = "principal") -> np.ndarray:
    """Devuelve la foto, enderezada y con la grilla 8x8 dibujada encima, tal
    cual queda dividida para reconocer_tablero — para mostrar visualmente que
    la detección geométrica (esquinas + perspectiva + alineación) encontró el
    tablero correctamente, sin pasar por la clasificación de piezas.

    Raises:
        ValueError: si no se detecta el tablero en la imagen (igual que
            reconocer_tablero).
    """
    esquinas, margen_porcentaje = esquinas_y_margen(imagen, camara)
    plano = enderezar_tablero(imagen, esquinas)
    lado = plano.shape[0]
    margen = int(lado * margen_porcentaje / 100)
    if margen:
        plano = plano[margen : lado - margen, margen : lado - margen]
    return dibujar_grilla_debug(plano)
