"""Rutas /vision/seguimiento/*: seguir la partida por diferencias, con una cámara y una calibración de mentira."""
import chess
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rutas.ruta_auth import get_current_user
from backend.servicios.vision import seguimiento_vivo, tablero
from backend.servicios.vision.test_seguimiento_jugadas import ESQ, _frame, _posicion_tras


@pytest.fixture
def cliente(monkeypatch):
    cuadros: list = []
    monkeypatch.setattr(tablero, "cargar_esquinas_calibradas", lambda *_a, **_k: ESQ)
    monkeypatch.setattr(seguimiento_vivo, "capturar_foto_tablero", lambda camara="principal": cuadros.pop(0))
    app.dependency_overrides[get_current_user] = lambda: 1
    try:
        c = TestClient(app)
        c.cuadros = cuadros
        yield c
    finally:
        seguimiento_vivo.detener()
        app.dependency_overrides.pop(get_current_user, None)


def test_sin_iniciar_no_hay_seguimiento(cliente) -> None:
    assert cliente.get("/vision/seguimiento").json() == {"activo": False}
    assert cliente.post("/vision/seguimiento/tick").status_code == 409


def test_sigue_una_jugada_y_se_puede_detener(cliente) -> None:
    inicio, tras_e4 = chess.STARTING_FEN, _posicion_tras("e2e4")
    assert cliente.post("/vision/seguimiento/iniciar", json={}).json()["fen"] == inicio
    cliente.cuadros += [_frame(inicio, semilla=s) for s in (1, 2, 3)] + [_frame(tras_e4, mano=True, semilla=4)] + [_frame(tras_e4, semilla=s) for s in (5, 6, 7, 8)]
    respuestas = [cliente.post("/vision/seguimiento/tick").json() for _ in range(8)]
    jugada = next(r for r in respuestas if r["estado"] == "jugada")
    assert jugada["jugada"] == "e4" and jugada["turno"] == "negras" and jugada["jugadas"] == ["e4"]
    assert cliente.get("/vision/seguimiento").json()["jugadas"] == ["e4"]
    assert cliente.delete("/vision/seguimiento").json() == {"activo": False}


def test_iniciar_valida_el_fen_y_la_calibracion(cliente, monkeypatch) -> None:
    assert cliente.post("/vision/seguimiento/iniciar", json={"fen": "esto no es un fen"}).status_code == 422
    monkeypatch.setattr(tablero, "cargar_esquinas_calibradas", lambda *_a, **_k: None)
    assert cliente.post("/vision/seguimiento/iniciar", json={}).status_code == 409


def test_fijar_la_posicion_tras_la_jugada_del_robot(cliente) -> None:
    cliente.post("/vision/seguimiento/iniciar", json={})
    nueva = _posicion_tras("e2e4", "e7e5")
    assert cliente.post("/vision/seguimiento/posicion", json={"fen": nueva}).json()["estado"] == "tomando_base"
    assert cliente.post("/vision/seguimiento/posicion", json={"fen": "x"}).status_code == 422


def test_tick_con_vista_deshacer_y_foto_base(cliente) -> None:
    inicio, tras_e4 = chess.STARTING_FEN, _posicion_tras("e2e4")
    cliente.post("/vision/seguimiento/iniciar", json={})
    cliente.cuadros += [_frame(inicio, semilla=s) for s in (1, 2, 3)] + [_frame(tras_e4, mano=True, semilla=4)] + [_frame(tras_e4, semilla=s) for s in (5, 6, 7)]
    respuestas = [cliente.post("/vision/seguimiento/tick?vista=true").json() for _ in range(7)]
    jugada = next(r for r in respuestas if r["estado"] == "jugada")
    assert jugada["vista"]["disponible"] and jugada["vista"]["candidatas"][0]["san"] == "e4" and jugada["puede_deshacer"]
    cliente.cuadros.append(_frame(tras_e4, semilla=8))
    assert "vista" not in cliente.post("/vision/seguimiento/tick").json()  # sin pedirla, no se manda
    assert cliente.get("/vision/seguimiento/vista").json()["jugada"] == "e4"
    assert cliente.post("/vision/seguimiento/foto-base").json()["estado"] == "tomando_base"
    assert cliente.post("/vision/seguimiento/deshacer").json()["deshecha"] == "e4"
    assert cliente.post("/vision/seguimiento/deshacer").status_code == 422  # ya no queda nada que deshacer


def test_vista_deshacer_y_foto_base_sin_seguimiento(cliente) -> None:
    assert cliente.get("/vision/seguimiento/vista").status_code == 409
    assert cliente.post("/vision/seguimiento/deshacer").status_code == 409
    assert cliente.post("/vision/seguimiento/foto-base").status_code == 409
