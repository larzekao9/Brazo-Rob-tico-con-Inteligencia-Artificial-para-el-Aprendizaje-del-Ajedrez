"""Captura una foto del tablero desde una cámara fija conectada a esta
máquina (HU1, RF06).

Solo toma la foto — pasarla por `reconocer_tablero` (en `reconocimiento.py`)
y mostrarla en una pantalla es responsabilidad de HU6, no de acá.

La fuente de la cámara se puede fijar por variable de entorno `CAMARA_FUENTE`
(mismo patrón que `DATABASE_URL` en `backend/database.py` — nada hardcodeado
en el código), para no depender de la webcam integrada de la laptop, que no
se puede reorientar hacia el tablero y suele tener peor calidad que un
celular:

- Sin configurar: cámara 0, la webcam por defecto de la máquina.
- Un número (ej. `CAMARA_FUENTE=1`): otro índice de cámara local — el caso
  de un celular conectado como cámara "virtual" vía USB con DroidCam o Iriun
  Webcam, que aparece como una webcam más para Windows.
- Una URL (ej. `CAMARA_FUENTE=http://192.168.1.23:8080/video`): un stream de
  red, el caso de la app "IP Webcam" (Android) — sirve tanto conectando el
  celular y la laptop a la misma red WiFi como compartiendo el propio
  hotspot del celular a la laptop (más estable si el WiFi de la facultad es
  lento, porque no depende de esa red para nada).
"""
from __future__ import annotations

import os
import time

import cv2
import numpy as np


def _fuente_por_defecto() -> int | str:
    """Resuelve `CAMARA_FUENTE` del entorno a lo que espera `cv2.VideoCapture`."""
    valor = os.environ.get("CAMARA_FUENTE", "").strip()
    if not valor:
        return 0
    if valor.isdigit():
        return int(valor)
    return valor


def capturar_foto_tablero(fuente: int | str | None = None) -> np.ndarray:
    """Toma una foto desde la cámara/fuente indicada.

    Args:
        fuente: índice de cámara local (int) o URL de un stream de red
            (str). Si no se pasa, se resuelve desde `CAMARA_FUENTE` (ver
            docstring del módulo).

    Returns:
        La imagen capturada, en el mismo formato BGR que espera
        `reconocer_tablero` (el que devuelve `cv2.imread`).

    Raises:
        RuntimeError: si no se pudo abrir la cámara/fuente o capturar un frame.
    """
    fuente_resuelta = fuente if fuente is not None else _fuente_por_defecto()
    camara = cv2.VideoCapture(fuente_resuelta)
    try:
        if not camara.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara/fuente {fuente_resuelta!r}")
        # Sin esto, algunas cámaras virtuales (ej. Iriun Webcam) devuelven un
        # frame con un formato/tiling raro en vez de la imagen completa —
        # pedir la resolución explícitamente antes de leer lo evita.
        camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        # Las cámaras virtuales a veces fallan el primer frame justo después
        # de abrirse (necesitan un instante para "calentar") — un par de
        # reintentos cortos alcanza, sin agregar demora perceptible a una
        # cámara física que siempre responde a la primera.
        for intento in range(3):
            exito, imagen = camara.read()
            if exito:
                return imagen
            time.sleep(0.3)
        raise RuntimeError(f"No se pudo capturar una foto de la fuente {fuente_resuelta!r}")
    finally:
        camara.release()
