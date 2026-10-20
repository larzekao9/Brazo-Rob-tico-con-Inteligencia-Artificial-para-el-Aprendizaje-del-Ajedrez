"""GET /brazo/estado: lo que muestra el panel Brazo del front, sin abrir conexiones."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.brazo import servicio_brazo


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(servicio_brazo, "_ejecutor", None)
    monkeypatch.setattr(servicio_brazo, "_ultima_jugada", None)
    app.dependency_overrides[get_current_facilitador] = lambda: 1
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_facilitador, None)


def test_modo_simulado_por_defecto(cliente, monkeypatch) -> None:
    monkeypatch.delenv("AJEDREZ_MODO_BRAZO", raising=False)
    assert cliente.get("/brazo/estado").json() == {"modo": "simulado", "host": None, "conectado": None, "ultima_jugada": None}


def test_modo_real_sin_ejecutor_no_esta_conectado_y_no_conecta(cliente, monkeypatch) -> None:
    monkeypatch.setenv("AJEDREZ_MODO_BRAZO", "real")
    monkeypatch.setenv("AJEDREZ_BRAZO_HOST", "192.0.2.1")
    cuerpo = cliente.get("/brazo/estado").json()
    assert cuerpo["modo"] == "real" and cuerpo["host"] == "192.0.2.1" and cuerpo["conectado"] is False
    assert servicio_brazo._ejecutor is None


def test_modo_real_con_ejecutor_esta_conectado(cliente, monkeypatch) -> None:
    monkeypatch.setenv("AJEDREZ_MODO_BRAZO", "real")
    monkeypatch.setattr(servicio_brazo, "_ejecutor", object())
    assert cliente.get("/brazo/estado").json()["conectado"] is True


def test_devuelve_la_ultima_jugada(cliente, monkeypatch) -> None:
    monkeypatch.setattr(servicio_brazo, "_ultima_jugada", "e2e4")
    assert cliente.get("/brazo/estado").json()["ultima_jugada"] == "e2e4"


def test_sin_token_es_rechazado() -> None:
    assert TestClient(app).get("/brazo/estado").status_code in (401, 403)
