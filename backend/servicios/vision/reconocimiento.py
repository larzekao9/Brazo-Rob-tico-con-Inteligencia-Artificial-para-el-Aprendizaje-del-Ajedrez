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
from backend.servicios.vision.piezas import clasificar_pieza
from backend.servicios.vision.tablero import (
    detectar_esquinas_tablero,
    dividir_en_casillas,
    enderezar_tablero,
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
    esquinas = detectar_esquinas_tablero(imagen)
    plano = enderezar_tablero(imagen, esquinas)
    casillas = dividir_en_casillas(plano)
    ocupacion = {nombre: clasificar_pieza(recorte) for nombre, recorte in casillas.items()}
    piezas_fen = _ocupacion_a_fen_piezas(ocupacion)
    return f"{piezas_fen} {turno} - - 0 1"
