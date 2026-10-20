"""Probador de piezas: foto de la cámara fija -> qué reconoce el modelo en cada casilla (sin guardar nada)."""
from __future__ import annotations

import base64

import cv2
import numpy as np

from backend.servicios.vision import piezas
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.reconocimiento import esquinas_y_margen
from backend.servicios.vision.tablero import dibujar_grilla_debug, dividir_en_casillas, enderezar_tablero, imagen_control_ampliada

_ABREVIATURA = {"pawn": "P", "knight": "N", "bishop": "B", "rook": "R", "queen": "Q", "king": "K"}


def _etiqueta_corta(clase: str) -> str:
    color, pieza = clase.split("-")
    letra = _ABREVIATURA[pieza]
    return letra if color == "white" else letra.lower()


def analizar_tablero(imagen: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    """Reconoce las 64 casillas de `imagen` y devuelve `(imagen anotada BGR, predicciones por casilla)`."""
    esquinas, margen = esquinas_y_margen(imagen)
    plano = enderezar_tablero(imagen, esquinas)
    recortes = dividir_en_casillas(plano, margen)
    nombres = list(recortes)
    resultados = piezas.clasificar_con_confianza([recortes[n] for n in nombres])
    vista = imagen_control_ampliada(imagen, esquinas) if not margen else dibujar_grilla_debug(plano)
    borde = vista.shape[0] * 0.12 if not margen else 0
    paso = (vista.shape[0] - 2 * borde) / 8
    casillas = []
    for nombre, top in zip(nombres, resultados):
        clase, confianza = top[0]
        casillas.append(
            {"casilla": nombre, "clase": clase, "confianza": round(confianza, 3), "alternativas": [{"clase": c, "confianza": round(p, 3)} for c, p in top[1:]]}
        )
        if clase == CLASE_VACIA:
            continue
        columna, fila = "abcdefgh".index(nombre[0]), 8 - int(nombre[1])
        x, y = int(borde + (columna + 0.5) * paso), int(borde + (fila + 0.5) * paso)
        color = (0, 200, 0) if confianza >= 0.8 else (0, 190, 255) if confianza >= 0.5 else (0, 0, 255)
        cv2.circle(vista, (x, y), int(paso * 0.3), color, -1)
        cv2.putText(vista, _etiqueta_corta(clase), (x - 12, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255) if clase.startswith("black") else (0, 0, 0), 2, cv2.LINE_AA)
    return vista, casillas


def probar_tablero(imagen: np.ndarray | None = None) -> dict:
    """Reconoce las 64 casillas de la foto (o de una nueva de la cámara) y devuelve predicciones e imagen anotada.

    Returns:
        `{"casillas": [{casilla, clase, confianza, alternativas}], "imagen": <JPEG en base64>}`; solo las casillas con pieza llevan
        etiqueta en la imagen (verde si la confianza es ≥ 0.8, ámbar ≥ 0.5, rojo menos).

    Raises:
        ValueError: tablero no detectado. RuntimeError: la cámara no está disponible.
    """
    if imagen is None:
        imagen = capturar_foto_tablero()
    vista, casillas = analizar_tablero(imagen)
    exito, buffer = cv2.imencode(".jpg", vista)
    if not exito:
        raise RuntimeError("No se pudo codificar la imagen")
    return {"casillas": casillas, "imagen": base64.b64encode(buffer.tobytes()).decode("ascii")}
