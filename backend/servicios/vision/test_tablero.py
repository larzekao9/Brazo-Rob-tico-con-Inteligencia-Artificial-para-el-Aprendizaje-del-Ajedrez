"""Tests de la detección geométrica del tablero.

Usan una imagen sintética generada acá mismo (un cuadrilátero inclinado con
un patrón de casillas) en vez de fotos reales, para que el test no dependa
de tener el dataset descargado — ese se prueba a mano por separado (ver
training/dataset_tablero/, ignorado por git).
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from backend.servicios.vision.tablero import (
    TAMANO_TABLERO_PLANO,
    detectar_esquinas_tablero,
    dibujar_grilla_debug,
    dividir_en_casillas,
    enderezar_tablero,
)

# Esquinas conocidas de un tablero inclinado dibujado sobre un fondo liso,
# en orden sup-izq, sup-der, inf-der, inf-izq.
ESQUINAS_ESPERADAS = np.array(
    [[150, 80], [750, 40], [780, 620], [120, 660]], dtype=np.float32
)


def _crear_imagen_de_prueba() -> np.ndarray:
    """Dibuja un cuadrilátero inclinado de color uniforme sobre fondo liso.

    No hace falta un patrón de casillas real acá — `detectar_esquinas_tablero`
    solo mira el contorno exterior, y un relleno parejo da un contorno limpio
    de 4 lados sin el ruido de bordes internos que metería una grilla dibujada
    a mano. La grilla real se prueba contra fotos reales por separado.
    """
    imagen = np.full((700, 900, 3), 200, dtype=np.uint8)  # fondo gris claro
    cv2.fillConvexPoly(imagen, ESQUINAS_ESPERADAS.astype(np.int32), (60, 60, 60))
    return imagen


def test_detectar_esquinas_tablero_encuentra_el_cuadrilatero() -> None:
    imagen = _crear_imagen_de_prueba()
    esquinas = detectar_esquinas_tablero(imagen)

    # Cada esquina detectada debe caer cerca de alguna esperada (no
    # necesariamente en el mismo orden exacto de índice a índice, pero
    # _ordenar_esquinas ya las devuelve en el orden sup-izq/sup-der/inf-der/inf-izq).
    assert esquinas.shape == (4, 2)
    for esperada, obtenida in zip(ESQUINAS_ESPERADAS, esquinas):
        assert np.linalg.norm(esperada - obtenida) < 15


def test_detectar_esquinas_sin_tablero_lanza_error() -> None:
    imagen_vacia = np.full((300, 300, 3), 128, dtype=np.uint8)  # fondo liso, sin contornos
    with pytest.raises(ValueError):
        detectar_esquinas_tablero(imagen_vacia)


def test_enderezar_tablero_devuelve_imagen_cuadrada() -> None:
    imagen = _crear_imagen_de_prueba()
    esquinas = detectar_esquinas_tablero(imagen)
    plano = enderezar_tablero(imagen, esquinas)
    assert plano.shape == (TAMANO_TABLERO_PLANO, TAMANO_TABLERO_PLANO, 3)


def test_dividir_en_casillas_devuelve_64_casillas_del_mismo_tamano() -> None:
    imagen = _crear_imagen_de_prueba()
    esquinas = detectar_esquinas_tablero(imagen)
    plano = enderezar_tablero(imagen, esquinas)
    casillas = dividir_en_casillas(plano)

    assert len(casillas) == 64
    assert set(casillas) == {f"{col}{fila}" for col in "abcdefgh" for fila in range(1, 9)}
    paso = TAMANO_TABLERO_PLANO // 8
    for recorte in casillas.values():
        assert recorte.shape == (paso, paso, 3)


def test_dibujar_grilla_debug_no_modifica_la_imagen_original() -> None:
    imagen = _crear_imagen_de_prueba()
    esquinas = detectar_esquinas_tablero(imagen)
    plano = enderezar_tablero(imagen, esquinas)
    copia = plano.copy()

    dibujar_grilla_debug(plano)

    assert np.array_equal(plano, copia)
