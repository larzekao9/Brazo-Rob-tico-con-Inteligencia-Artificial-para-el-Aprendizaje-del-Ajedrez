"""Panel de control del brazo contra el emulador en memoria (sin hardware)."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.brazo import control_brazo


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(control_brazo, "ARCHIVO_CONFIGURACIONES", tmp_path / "configuraciones.json")
    app.dependency_overrides[get_current_facilitador] = lambda: 1
    try:
        yield TestClient(app)
    finally:
        control_brazo.desconectar()
        app.dependency_overrides.pop(get_current_facilitador, None)


def _conectar(c):
    r = c.post("/brazo/control/conectar", json={"emulador": True})
    assert r.status_code == 200, r.text
    return r.json()


def test_sin_conexion_los_comandos_dan_409(cliente) -> None:
    assert cliente.get("/brazo/control/estado").json()["conectado"] is False
    assert cliente.post("/brazo/control/habilitar").status_code == 409
    assert cliente.post("/brazo/control/mover-pieza", json={"origen": "e2", "destino": "e4"}).status_code == 409


def test_conectar_no_habilita_ni_mueve_y_habilitar_si(cliente) -> None:
    estado = _conectar(cliente)
    assert estado["conectado"] and estado["emulador"] and estado["modo"] != 5 and len(estado["pose"]) == 6 and len(estado["angulos"]) == 6
    assert cliente.post("/brazo/control/mover-pieza", json={"origen": "e2", "destino": "e4"}).status_code == 409  # sin habilitar
    assert cliente.post("/brazo/control/habilitar").json()["modo"] == 5
    assert cliente.post("/brazo/control/conectar", json={"emulador": True}).status_code == 409


def test_parametros_validacion_y_configuraciones(cliente) -> None:
    _conectar(cliente)
    r = cliente.put("/brazo/control/parametros", json={"valores": {"velocidad_global": 35, "fuerza": 40, "altura_segura_mm": 90}})
    assert r.status_code == 200 and r.json()["velocidad_global"] == 35 and r.json()["fuerza"] == 40
    assert cliente.put("/brazo/control/parametros", json={"valores": {"velocidad_global": 500}}).status_code == 422
    assert cliente.put("/brazo/control/parametros", json={"valores": {"fuerza": 5}}).status_code == 422  # la pinza exige 20 o más
    assert cliente.put("/brazo/control/parametros", json={"valores": {"inventado": 1}}).status_code == 422

    assert cliente.post("/brazo/control/configuraciones", json={"nombre": "Suave", "descripcion": "lento"}).json()[0]["nombre"] == "Suave"
    cliente.put("/brazo/control/parametros", json={"valores": {"velocidad_global": 80}})
    assert cliente.post("/brazo/control/configuraciones/Suave/aplicar").json()["velocidad_global"] == 35
    assert cliente.post("/brazo/control/configuraciones/Nada/aplicar").status_code == 404
    assert cliente.delete("/brazo/control/configuraciones/Suave").json() == []


def test_ensayo_lista_los_pasos_sin_mover(cliente) -> None:
    _conectar(cliente)
    pasos = cliente.post("/brazo/control/mover-pieza/ensayo", json={"origen": "e2", "destino": "e4"}).json()
    assert len(pasos) == 10 and pasos[1]["pose"] is not None and pasos[0]["pose"] is None
    assert cliente.post("/brazo/control/mover-pieza/ensayo", json={"origen": "z9", "destino": "e4"}).status_code == 422
    assert cliente.post("/brazo/control/mover-pieza/ensayo", json={"origen": "e2", "destino": "e2"}).status_code == 422


def _esperar_tarea(c, estados=("terminada", "error", "cancelada"), limite=60):
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        tarea = c.get("/brazo/control/estado").json()["tarea"]
        if tarea["estado"] in estados:
            return tarea
        time.sleep(0.3)
    raise AssertionError("la tarea no terminó")


def test_mover_pieza_en_el_emulador(cliente) -> None:
    _conectar(cliente)
    cliente.post("/brazo/control/habilitar")
    r = cliente.post("/brazo/control/mover-pieza", json={"origen": "e2", "destino": "e4", "tipo_pieza": "p"})
    assert r.status_code == 200 and r.json()["tarea"]["estado"] == "ejecutando"
    tarea = _esperar_tarea(cliente)
    assert tarea["estado"] == "terminada", tarea


def test_parar_cancela_la_secuencia(cliente) -> None:
    _conectar(cliente)
    cliente.post("/brazo/control/habilitar")
    cliente.post("/brazo/control/mover-pieza", json={"origen": "e2", "destino": "e4", "tipo_pieza": "p"})
    time.sleep(0.5)
    cliente.post("/brazo/control/parar")
    tarea = _esperar_tarea(cliente)
    assert tarea["estado"] in ("cancelada", "terminada")
