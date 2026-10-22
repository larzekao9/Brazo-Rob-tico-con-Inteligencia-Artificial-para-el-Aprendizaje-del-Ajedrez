

import pytest


@pytest.fixture(autouse=True)
def _sin_modelo_de_dos_vistas_real(tmp_path, monkeypatch):
    """Las pruebas no deben depender del modelo de dos vistas que haya entrenado el usuario en `training/checkpoints/`."""
    from backend.servicios.vision import piezas

    monkeypatch.setattr(piezas, "RUTA_DOS_VISTAS", tmp_path / "sin_dos_vistas.pt")
    piezas.invalidar_modelo()
    yield
    piezas.invalidar_modelo()
