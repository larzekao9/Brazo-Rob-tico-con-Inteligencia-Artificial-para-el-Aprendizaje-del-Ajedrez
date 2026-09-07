"""Tests de la clasificación de piezas.

`clasificar_pieza` necesita el checkpoint que genera
`training/entrenar_clasificador_piezas.py` — ignorado por git (ver
CLAUDE.md), así que el test que lo usa se saltea si nadie lo entrenó
todavía en esta máquina. El test de manejo de error sí corre siempre.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.servicios.vision import piezas
from backend.servicios.vision.modelo_piezas import CLASES

CHECKPOINT_DISPONIBLE = piezas.RUTA_CHECKPOINT.exists()


def test_clasificar_pieza_sin_checkpoint_lanza_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(piezas, "RUTA_CHECKPOINT", tmp_path / "no_existe.pt")
    monkeypatch.setattr(piezas, "_modelo", None)
    monkeypatch.setattr(piezas, "_clases", None)
    with pytest.raises(FileNotFoundError):
        piezas.clasificar_pieza(np.zeros((100, 100, 3), dtype=np.uint8))


@pytest.mark.skipif(not CHECKPOINT_DISPONIBLE, reason="No hay checkpoint entrenado en esta máquina")
def test_clasificar_pieza_devuelve_una_clase_valida() -> None:
    recorte = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    etiqueta = piezas.clasificar_pieza(recorte)
    assert etiqueta in CLASES
