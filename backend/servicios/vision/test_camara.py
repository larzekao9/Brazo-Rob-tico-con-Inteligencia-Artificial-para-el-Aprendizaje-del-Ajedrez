"""Tests de la captura por cámara.

El test contra una cámara real se saltea si esta máquina no tiene ninguna
conectada — el de manejo de error (índice inválido) sí corre siempre, sin
necesitar hardware.
"""
from __future__ import annotations

import cv2
import pytest

from backend.servicios.vision.camara import _api_por_defecto, _fuente_por_defecto, capturar_foto_tablero


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


def test_api_por_defecto_sin_configurar_deja_elegir_a_opencv(monkeypatch) -> None:
    monkeypatch.delenv("CAMARA_API", raising=False)

    assert _api_por_defecto() is None


def test_api_por_defecto_acepta_msmf_y_dshow_sin_importar_mayusculas(monkeypatch) -> None:
    monkeypatch.setenv("CAMARA_API", "msmf")
    assert _api_por_defecto() == cv2.CAP_MSMF
    monkeypatch.setenv("CAMARA_API", " DShow ")
    assert _api_por_defecto() == cv2.CAP_DSHOW
    monkeypatch.setenv("CAMARA_API", "otra")
    assert _api_por_defecto() is None


def test_rotacion_valida_y_aplica_el_giro(tmp_path, monkeypatch) -> None:
    import numpy as np

    from backend.servicios.vision import camara

    monkeypatch.setattr(camara, "ARCHIVO_PREFERENCIA", tmp_path / "camara.json")
    monkeypatch.setattr(camara, "_preferencia", {})
    monkeypatch.delenv("CAMARA_ROTACION", raising=False)
    assert camara.fijar_rotacion(180) == 180 and camara.rotacion_actual() == 180
    imagen = np.zeros((2, 3, 3), dtype=np.uint8)
    imagen[0, 0] = 255
    assert camara._rotar(imagen)[1, 2].tolist() == [255, 255, 255]
    camara.fijar_rotacion(90)
    assert camara._rotar(imagen).shape == (3, 2, 3)
    assert camara.rotacion_actual("secundaria") == 0  # cada cámara tiene su giro
    with pytest.raises(ValueError):
        camara.fijar_rotacion(45)
    with pytest.raises(ValueError):
        camara.fijar_rotacion(90, "tercera")


def test_la_camara_y_el_giro_elegidos_se_recuerdan_por_camara(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import camara

    monkeypatch.setattr(camara, "ARCHIVO_PREFERENCIA", tmp_path / "camara.json")
    monkeypatch.setattr(camara, "_preferencia", None)
    monkeypatch.setenv("CAMARA_FUENTE", "3")
    monkeypatch.delenv("CAMARA_FUENTE_2", raising=False)
    assert camara._fuente_por_defecto() == 3  # sin preferencia manda el .env
    assert camara._fuente_por_defecto("secundaria") is None and camara.camaras_configuradas() == ["principal"]
    camara._guardar_preferencia("principal", fuente="1")
    camara._guardar_preferencia("secundaria", fuente="2")
    camara.fijar_rotacion(90, "secundaria")
    assert camara._fuente_por_defecto() == 1 and camara.camaras_configuradas() == ["principal", "secundaria"]
    monkeypatch.setattr(camara, "_preferencia", None)  # "reinicio": se vuelve a leer del archivo
    assert camara._fuente_por_defecto("secundaria") == 2 and camara.rotacion_actual("secundaria") == 90


def test_preferencia_en_el_formato_viejo_se_lee_como_camara_principal(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import camara

    archivo = tmp_path / "camara.json"
    archivo.write_text('{"fuente": "2", "rotacion": 180}', encoding="utf-8")
    monkeypatch.setattr(camara, "ARCHIVO_PREFERENCIA", archivo)
    monkeypatch.setattr(camara, "_preferencia", None)
    assert camara._fuente_por_defecto() == 2 and camara.rotacion_actual() == 180


def test_dos_camaras_no_pueden_usar_la_misma_fuente(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import camara

    monkeypatch.setattr(camara, "ARCHIVO_PREFERENCIA", tmp_path / "camara.json")
    monkeypatch.setattr(camara, "_preferencia", {"principal": {"fuente": "0"}})
    with pytest.raises(ValueError):
        camara.seleccionar_fuente(0, "secundaria")
