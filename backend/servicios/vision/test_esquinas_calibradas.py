"""Esquinas del tablero marcadas una sola vez para una cámara fija: guardado, lectura y enderezado."""
import json

import cv2
import numpy as np
import pytest

from backend.servicios.vision.tablero import (
    cargar_esquinas_calibradas,
    dividir_en_casillas,
    enderezar_tablero,
    guardar_esquinas_calibradas,
)

# Tablero girado como en la mesa real: las blancas a la derecha, o sea a1 abajo a la derecha de la foto.
ESQUINAS = {"a1": (300.0, 300.0), "h1": (300.0, 100.0), "h8": (100.0, 100.0), "a8": (100.0, 300.0)}


def test_sin_archivo_no_hay_calibracion(tmp_path) -> None:
    assert cargar_esquinas_calibradas(tmp_path / "no_existe.json") is None


def test_guarda_y_lee_las_esquinas_en_el_orden_del_enderezado(tmp_path) -> None:
    ruta = tmp_path / "calibracion" / "esquinas.json"

    guardar_esquinas_calibradas(ESQUINAS, ruta)
    leidas = cargar_esquinas_calibradas(ruta)

    assert leidas.shape == (4, 2) and leidas.dtype == np.float32
    assert leidas.tolist() == [[100, 300], [100, 100], [300, 100], [300, 300]]  # a8, h8, h1, a1


def test_no_guarda_si_falta_una_esquina(tmp_path) -> None:
    with pytest.raises(ValueError):
        guardar_esquinas_calibradas({k: v for k, v in ESQUINAS.items() if k != "a8"}, tmp_path / "x.json")


def test_un_archivo_danado_da_error_claro(tmp_path) -> None:
    ruta = tmp_path / "roto.json"
    ruta.write_text("esto no es json", encoding="utf-8")
    incompleto = tmp_path / "incompleto.json"
    incompleto.write_text(json.dumps({"a1": [1, 2]}), encoding="utf-8")

    with pytest.raises(ValueError, match="volvé a calibrar"):
        cargar_esquinas_calibradas(ruta)
    with pytest.raises(ValueError, match="volvé a calibrar"):
        cargar_esquinas_calibradas(incompleto)


def test_el_tablero_enderezado_queda_con_a1_abajo_a_la_izquierda_aunque_la_foto_este_girada(tmp_path) -> None:
    # Foto de 400x400 con un marcador rojo en la casilla a1 (abajo a la derecha de la foto) y otro azul en h8 (arriba a la izquierda).
    foto = np.full((400, 400, 3), 255, np.uint8)
    cv2.rectangle(foto, (250, 250), (300, 300), (0, 0, 255), -1)  # a1
    cv2.rectangle(foto, (100, 100), (150, 150), (255, 0, 0), -1)  # h8
    ruta = tmp_path / "esquinas.json"
    guardar_esquinas_calibradas(ESQUINAS, ruta)

    plano = enderezar_tablero(foto, cargar_esquinas_calibradas(ruta), tamano=400)
    casillas = dividir_en_casillas(plano, margen_porcentaje=0)

    def color_central(nombre: str) -> tuple[int, int, int]:
        recorte = casillas[nombre]
        centro = recorte[recorte.shape[0] // 2, recorte.shape[1] // 2]
        return int(centro[0]), int(centro[1]), int(centro[2])

    assert color_central("a1") == (0, 0, 255) and color_central("h8") == (255, 0, 0)
    assert color_central("e4") == (255, 255, 255)
