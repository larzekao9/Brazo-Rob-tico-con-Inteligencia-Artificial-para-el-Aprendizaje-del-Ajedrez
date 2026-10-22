"""Rutas /vision/lente con un tablero sintético visto desde posiciones conocidas (sin cámara)."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rutas import ruta_vision_lente
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.vision import camara as servicio_camara
from backend.servicios.vision import tablero
from backend.servicios.vision.test_geometria3d import _foto_del_tablero

POSICIONES = [(120, -250, 420), (300, -150, 380), (-60, -200, 360), (120, 500, 400)]


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    monkeypatch.setattr(servicio_camara, "_preferencia", {})
    imagen, esquinas, _ = _foto_del_tablero()
    tablero.guardar_esquinas_calibradas(dict(zip(("a1", "h1", "h8", "a8"), esquinas.tolist())))
    turno = iter(POSICIONES * 3)
    estado = {"actual": imagen}

    def capturar(*_a, **_k):
        return estado["actual"]

    monkeypatch.setattr(ruta_vision_lente, "capturar_foto_tablero", capturar)
    cliente = TestClient(app)
    cliente.siguiente_vista = lambda: estado.update(actual=_foto_del_tablero(next(turno))[0])
    app.dependency_overrides[get_current_facilitador] = lambda: 1
    try:
        yield cliente
    finally:
        app.dependency_overrides.pop(get_current_facilitador, None)


def test_estado_da_el_lente_supuesto_y_la_posicion_de_la_camara(cliente) -> None:
    r = cliente.get("/vision/lente/estado").json()
    assert r["lente"]["origen"] == "supuesto" and r["diagnostico"]["altura_mm"] > 0 and r["aviso"] is None
    assert r["casilla_mm"] == 30 and r["altura_pieza_mm"] == 60 and r["fotos_guardadas"] == 0


def test_sin_calibrar_el_tablero_avisa(cliente, tmp_path) -> None:
    (tmp_path / "esquinas.json").unlink()
    r = cliente.get("/vision/lente/estado").json()
    assert r["diagnostico"] is None and "Calibrá primero" in r["aviso"]
    assert cliente.get("/vision/lente/vista").status_code == 409


def test_agregar_fotos_calcular_y_borrar_el_lente(cliente) -> None:
    for _ in POSICIONES:
        cliente.siguiente_vista()
        assert cliente.post("/vision/lente/foto").json()["detectada"] is True
    assert cliente.get("/vision/lente/estado").json()["fotos_guardadas"] == 4
    r = cliente.post("/vision/lente/calcular").json()
    assert r["guardado"] is True and r["lente"]["origen"] == "autocalibrado" and 60 < r["lente"]["fov_horizontal"] < 100
    assert cliente.get("/vision/lente/estado").json()["lente"]["origen"] == "autocalibrado"
    assert cliente.delete("/vision/lente").json() == {"borrado": True}
    assert cliente.get("/vision/lente/estado").json()["lente"]["origen"] == "supuesto"
    assert cliente.post("/vision/lente/calcular").status_code == 422  # ya no hay fotos


def test_fov_manual_y_vista_de_cajas(cliente) -> None:
    assert cliente.post("/vision/lente/fov", json={"grados": 66}).json()["lente"]["origen"] == "manual"
    r = cliente.get("/vision/lente/vista", params={"casillas": "e4,a1"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert cliente.post("/vision/lente/fov", json={"grados": 5}).status_code == 422
    assert cliente.get("/vision/lente/estado", params={"camara": "otra"}).status_code == 422
