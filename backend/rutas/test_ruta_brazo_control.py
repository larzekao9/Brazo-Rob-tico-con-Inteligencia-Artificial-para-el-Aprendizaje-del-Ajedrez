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
    assert len(pasos) == 11 and pasos[0]["paso"].startswith("Ir a la posición inicial") and pasos[2]["pose"] is not None and pasos[0]["pose"] is None
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


def test_inicializar_la_pinza_despues_de_parar_levanta_el_bloqueo(cliente) -> None:
    """Tras «Parar» el cliente rechaza escribir a la pinza («Cancelado por el usuario»); inicializarla es una acción explícita y lo levanta."""
    _conectar(cliente)
    cliente.post("/brazo/control/habilitar")
    assert cliente.post("/brazo/control/parar").status_code == 200
    r = cliente.post("/brazo/control/pinza/inicializar")
    assert r.status_code == 200, r.text


def _esperar_tarea(c, limite=20):
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        tarea = c.get("/brazo/control/estado").json()["tarea"]
        if tarea["estado"] != "ejecutando":
            return tarea
        time.sleep(0.1)
    raise AssertionError("la tarea no terminó")


def test_mover_articulaciones_y_relativo(cliente) -> None:
    _conectar(cliente)
    assert cliente.post("/brazo/control/mover-articulaciones", json={"angulos": [0, 0, 0, 0, 0, 0]}).status_code == 409  # sin habilitar
    cliente.post("/brazo/control/habilitar")
    assert cliente.post("/brazo/control/mover-articulaciones", json={"angulos": [0, 0, 0]}).status_code == 422
    assert cliente.post("/brazo/control/mover-articulaciones", json={"angulos": [0, 200, 0, 0, 0, 0]}).status_code == 422  # J2 fuera de rango
    objetivo = [-30, 85, -80, -98, 90, -75]
    assert cliente.post("/brazo/control/mover-articulaciones", json={"angulos": objetivo}).status_code == 200
    assert _esperar_tarea(cliente)["estado"] == "terminada"
    angulos = cliente.get("/brazo/control/estado").json()["angulos"]
    assert all(abs(a - b) < 1.0 for a, b in zip(angulos, objetivo))
    antes = cliente.get("/brazo/control/estado").json()["pose"]
    assert cliente.post("/brazo/control/mover-relativo", json={"dz": 150}).status_code == 422  # más de 100 mm
    assert cliente.post("/brazo/control/mover-relativo", json={"dz": 20}).status_code == 200
    tarea = _esperar_tarea(cliente)
    assert tarea["estado"] == "terminada", tarea["mensaje"]
    despues = cliente.get("/brazo/control/estado").json()["pose"]
    assert abs((despues[2] - antes[2]) - 20) < 1.0


def test_posicion_inicial(cliente) -> None:
    _conectar(cliente)
    assert cliente.post("/brazo/control/posicion-inicial").status_code == 409  # sin habilitar
    cliente.post("/brazo/control/habilitar")
    assert cliente.post("/brazo/control/posicion-inicial").status_code == 200
    tarea = _esperar_tarea(cliente)
    assert tarea["estado"] == "terminada", tarea["mensaje"]
    cero = control_brazo._ejecutor().angulos_cero
    angulos = cliente.get("/brazo/control/estado").json()["angulos"]
    assert all(abs(a - b) < 1.0 for a, b in zip(angulos, cero))
