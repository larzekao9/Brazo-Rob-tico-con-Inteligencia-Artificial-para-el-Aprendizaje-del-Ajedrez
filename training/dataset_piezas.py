"""Genera un dataset de casillas etiquetadas a partir de `dataset_tablero/`.

`training/dataset_tablero/` (ignorado por git, ver README) trae fotos reales
de tableros con cajas delimitadoras por pieza (formato COCO), pero no dice
qué casilla ocupa cada pieza. Este módulo lo resuelve reusando la detección
de esquinas de `backend/servicios/vision/tablero.py`: encuentra el tablero en
la foto, lo endereza, y proyecta el punto de apoyo de cada caja (su base) a
través de esa misma transformación para saber en qué casilla cae. Así se
arma automáticamente un dataset de (recorte de casilla, etiqueta) sin anotar
nada a mano.

Clases: "vacia" + las 12 combinaciones de color y tipo de pieza que trae el
dataset de Roboflow (`white-pawn`, `black-knight`, etc.) — definidas en
`backend/servicios/vision/modelo_piezas.py`, no acá, porque son parte del
contrato del servicio de visión, no un detalle de cómo se arma el dataset.
Se ignoran las categorías "pieces" y "bishop" del dataset original — son
restos sin anotaciones reales o mal etiquetados (un solo caso en las 2869
anotaciones).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import cv2
import numpy as np

from backend.servicios.vision.modelo_piezas import CATEGORIAS_VALIDAS, CLASE_VACIA
from backend.servicios.vision.tablero import (
    TAMANO_TABLERO_PLANO,
    detectar_esquinas_tablero,
    dividir_en_casillas,
    enderezar_tablero,
)


def _punto_a_casilla(punto: tuple[float, float], tamano: int = TAMANO_TABLERO_PLANO) -> str | None:
    """Mapea un punto de la imagen ya enderezada a su casilla (ver `dividir_en_casillas`).

    Devuelve None si el punto cae fuera del tablero (esquinas mal detectadas).
    """
    x, y = punto
    if not (0 <= x < tamano and 0 <= y < tamano):
        return None
    paso = tamano // 8
    fila, columna = int(y // paso), int(x // paso)
    return f"{'abcdefgh'[columna]}{8 - fila}"


def _muestras_de_una_imagen(
    imagen: np.ndarray, anotaciones: list[dict], id_a_categoria: dict[int, str]
) -> list[tuple[np.ndarray, str]]:
    """Extrae (recorte_de_casilla, etiqueta) de una foto y sus anotaciones COCO."""
    esquinas = detectar_esquinas_tablero(imagen)  # puede lanzar ValueError, lo maneja el caller
    matriz = cv2.getPerspectiveTransform(
        esquinas,
        np.array(
            [[0, 0], [TAMANO_TABLERO_PLANO - 1, 0],
             [TAMANO_TABLERO_PLANO - 1, TAMANO_TABLERO_PLANO - 1], [0, TAMANO_TABLERO_PLANO - 1]],
            dtype=np.float32,
        ),
    )
    plano = enderezar_tablero(imagen, esquinas)
    casillas = dividir_en_casillas(plano)

    ocupadas: dict[str, str] = {}
    for anotacion in anotaciones:
        categoria = id_a_categoria[anotacion["category_id"]]
        if categoria not in CATEGORIAS_VALIDAS:
            continue
        x, y, ancho, alto = anotacion["bbox"]
        base_pieza = np.array([[[x + ancho / 2, y + alto]]], dtype=np.float32)  # punto de apoyo
        base_plana = cv2.perspectiveTransform(base_pieza, matriz)[0, 0]
        nombre_casilla = _punto_a_casilla(tuple(base_plana))
        if nombre_casilla is not None:
            ocupadas[nombre_casilla] = categoria

    muestras = [(casillas[casilla], etiqueta) for casilla, etiqueta in ocupadas.items()]
    vacias = [casillas[casilla] for casilla in casillas if casilla not in ocupadas]
    random.shuffle(vacias)
    # tantas casillas vacías como piezas encontradas, para no desbalancear tanto
    muestras += [(recorte, CLASE_VACIA) for recorte in vacias[: max(len(ocupadas), 1)]]
    return muestras


def construir_dataset(carpeta_split: str | Path) -> list[tuple[np.ndarray, str]]:
    """Recorre un split (`train`, `valid` o `test`) de `dataset_tablero/` y arma las muestras.

    Las fotos donde no se detectan las esquinas del tablero se descartan (son
    ~5% del dataset — fondos o ángulos donde el contorno no se distingue bien).
    """
    carpeta_split = Path(carpeta_split)
    with open(carpeta_split / "_annotations.coco.json", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    id_a_categoria = {c["id"]: c["name"] for c in datos["categories"]}
    anotaciones_por_imagen: dict[int, list[dict]] = {}
    for anotacion in datos["annotations"]:
        anotaciones_por_imagen.setdefault(anotacion["image_id"], []).append(anotacion)

    muestras: list[tuple[np.ndarray, str]] = []
    for info_imagen in datos["images"]:
        imagen = cv2.imread(str(carpeta_split / info_imagen["file_name"]))
        if imagen is None:
            continue
        try:
            muestras += _muestras_de_una_imagen(
                imagen, anotaciones_por_imagen.get(info_imagen["id"], []), id_a_categoria
            )
        except ValueError:
            continue  # no se detectó el tablero en esta foto, se descarta
    return muestras
