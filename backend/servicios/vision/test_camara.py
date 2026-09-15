"""Tests de la captura por cámara.

El test contra una cámara real se saltea si esta máquina no tiene ninguna
conectada — el de manejo de error (índice inválido) sí corre siempre, sin
necesitar hardware.
"""
from __future__ import annotations

import cv2
import pytest

from backend.servicios.vision.camara import _fuente_por_defecto, capturar_foto_tablero


def _hay_camara_disponible() -> bool:
    camara = cv2.VideoCapture(0)
    disponible = camara.isOpened()
    camara.release()
    return disponible


CAMARA_DISPONIBLE = _hay_camara_disponible()


def test_capturar_foto_camara_invalida_lanza_error() -> None:
    with pytest.raises(RuntimeError):
        capturar_foto_tablero(fuente=99)


@pytest.mark.skipif(not CAMARA_DISPONIBLE, reason="No hay cámara conectada en esta máquina")
def test_capturar_foto_tablero_devuelve_imagen_valida() -> None:
    imagen = capturar_foto_tablero(fuente=0)
    assert imagen is not None
    assert imagen.ndim == 3


def test_fuente_por_defecto_es_cero_sin_variable_de_entorno(monkeypatch) -> None:
    monkeypatch.delenv("CAMARA_FUENTE", raising=False)
    assert _fuente_por_defecto() == 0


def test_fuente_por_defecto_interpreta_numero_como_indice(monkeypatch) -> None:
    monkeypatch.setenv("CAMARA_FUENTE", "2")
    assert _fuente_por_defecto() == 2


def test_fuente_por_defecto_interpreta_url_como_string(monkeypatch) -> None:
    monkeypatch.setenv("CAMARA_FUENTE", "http://192.168.1.23:8080/video")
    assert _fuente_por_defecto() == "http://192.168.1.23:8080/video"
