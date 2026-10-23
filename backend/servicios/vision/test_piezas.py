"""Tests de la clasificación de piezas.

`clasificar_pieza` necesita el checkpoint que genera
`training/entrenar_clasificador_piezas.py` — ignorado por git (ver
las reglas del proyecto), así que el test que lo usa se saltea si nadie lo entrenó
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


def test_invalidar_modelo_descarta_el_cache() -> None:
    piezas._modelo = object()
    piezas._clases = ["vacia"]
    piezas.invalidar_modelo()
    assert piezas._modelo is None and piezas._clases is None


def test_carga_un_checkpoint_torchscript_como_el_que_exporta_colab(monkeypatch, tmp_path) -> None:
    """El notebook de Colab guarda la red completa en TorchScript (con la normalización adentro); el backend la usa sin torchvision."""
    import io

    import torch

    class Normalizada(torch.nn.Module):  # como `Clasificador` del notebook: normaliza adentro y clasifica
        def __init__(self) -> None:
            super().__init__()
            self.capa = torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten(), torch.nn.Linear(3, len(CLASES)))
            self.register_buffer("media", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.capa(x - self.media)

    red = Normalizada().eval()
    buffer = io.BytesIO()
    torch.jit.save(torch.jit.trace(red, torch.rand(1, 3, 128, 128)), buffer)
    ruta = tmp_path / "clasificador_piezas.pt"
    torch.save({"formato": "torchscript", "torchscript": buffer.getvalue(), "clases": list(CLASES), "tamano": 128, "recorte": "ampliado"}, ruta)
    monkeypatch.setattr(piezas, "RUTA_CHECKPOINT", ruta)
    monkeypatch.setattr(piezas, "_modelo", None)

    recortes = [np.random.randint(0, 255, (96, 96, 3), dtype=np.uint8) for _ in range(3)]
    probs = piezas.probabilidades(recortes)
    assert probs.shape == (3, len(CLASES)) and np.allclose(probs.sum(axis=1), 1, atol=1e-5)
    assert piezas.modo_recorte() == "ampliado" and piezas.clases_del_modelo() == list(CLASES)
    with torch.no_grad():
        esperado = torch.softmax(red(torch.stack([piezas.preprocesar_recorte(r, 128) for r in recortes])), dim=1).numpy()
    assert np.allclose(probs, esperado, atol=1e-5)
    piezas.invalidar_modelo()
