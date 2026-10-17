"""GET/PUT/DELETE /vision/calibracion con un archivo de esquinas temporal."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.vision import tablero

ESQUINAS = {"a1": [100, 400], "h1": [500, 410], "h8": [490, 20], "a8": [110, 30]}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    app.dependency_overrides[get_current_facilitador] = lambda: 1
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_facilitador, None)


def test_get_sin_calibrar(cliente) -> None:
    assert cliente.get("/vision/calibracion").json() == {"calibrada": False, "esquinas": None}


def test_put_guarda_y_get_lo_devuelve(cliente) -> None:
    respuesta = cliente.put("/vision/calibracion", json={"esquinas": ESQUINAS})
    assert respuesta.status_code == 200
    assert respuesta.json()["calibrada"] is True
    assert respuesta.json()["esquinas"]["h1"] == [500.0, 410.0]
    assert cliente.get("/vision/calibracion").json() == respuesta.json()
    assert tablero.cargar_esquinas_calibradas() is not None


@pytest.mark.parametrize(
    "esquinas",
    [
        {"a1": [100, 400], "h1": [500, 410], "h8": [490, 20]},
        {**ESQUINAS, "h1": [-5, 410]},
        {**ESQUINAS, "h1": [500]},
        {"a1": [100, 400], "h1": [500, 410], "h8": [110, 30], "a8": [490, 20]},
        {"a1": [10, 10], "h1": [20, 10], "h8": [20, 20], "a8": [10, 20]},
    ],
)
def test_put_invalido_es_422_y_no_guarda(cliente, esquinas) -> None:
    assert cliente.put("/vision/calibracion", json={"esquinas": esquinas}).status_code == 422
    assert cliente.get("/vision/calibracion").json()["calibrada"] is False


def test_put_numero_no_finito_es_422(cliente) -> None:
    cuerpo = '{"esquinas": {"a1": [100, 400], "h1": [1e999, 410], "h8": [490, 20], "a8": [110, 30]}}'
    respuesta = cliente.put("/vision/calibracion", content=cuerpo, headers={"content-type": "application/json"})
    assert respuesta.status_code == 422


def test_delete_borra_la_calibracion(cliente) -> None:
    cliente.put("/vision/calibracion", json={"esquinas": ESQUINAS})
    respuesta = cliente.delete("/vision/calibracion")
    assert respuesta.status_code == 200 and respuesta.json() == {"calibrada": False, "esquinas": None}
    assert cliente.delete("/vision/calibracion").status_code == 200


def test_sin_token_es_rechazado(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    anonimo = TestClient(app)
    assert anonimo.get("/vision/calibracion").status_code in (401, 403)
    assert anonimo.put("/vision/calibracion", json={"esquinas": ESQUINAS}).status_code in (401, 403)
    assert anonimo.delete("/vision/calibracion").status_code in (401, 403)
