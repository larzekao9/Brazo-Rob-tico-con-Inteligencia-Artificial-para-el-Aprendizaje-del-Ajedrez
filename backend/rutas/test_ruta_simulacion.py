"""Rutas /simulacion (abrir la ventana 3D en vivo) contra una SQLite en memoria.

`subprocess.Popen` se mockea siempre en estos tests — dejarlo correr de
verdad abriría una ventana real de PyBullet.
"""
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.rutas.ruta_auth import get_db
import backend.servicios.partida.servicio_simulacion_3d as servicio_simulacion_3d_mod

JUGADOR = {"email": "sala-control@test.com", "nombre": "Jugadora", "password": "secreto1"}


@pytest.fixture
def contexto():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    crear_tablas(engine)
    fabrica = crear_fabrica_sesiones(engine)

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    override_anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _db
    cliente = TestClient(app)
    respuesta = cliente.post("/auth/registro", json=JUGADOR)
    token = respuesta.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    try:
        yield cliente, headers, token
    finally:
        if override_anterior is not None:
            app.dependency_overrides[get_db] = override_anterior
        else:
            app.dependency_overrides.pop(get_db, None)


def test_abrir_ventana_3d_lanza_proceso_con_los_argumentos_esperados(contexto, monkeypatch) -> None:
    cliente, headers, token = contexto
    partida_id = cliente.post("/partida", json={"nivel": 10}, headers=headers).json()["id"]

    monkeypatch.setattr(servicio_simulacion_3d_mod, "PYTHON_SIMULACION", sys.executable)
    llamadas = []
    monkeypatch.setattr(
        servicio_simulacion_3d_mod.subprocess,
        "Popen",
        lambda argumentos, cwd=None: llamadas.append((argumentos, cwd)),
    )

    respuesta = cliente.post(
        "/simulacion/abrir-ventana-3d", json={"partida_id": partida_id}, headers=headers
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"lanzado": True}
    assert len(llamadas) == 1
    argumentos, cwd = llamadas[0]
    assert argumentos == [
        sys.executable,
        "-m",
        "backend.servicios.simulacion.ver_partida_en_vivo",
        partida_id,
        token,
    ]
    assert cwd == str(servicio_simulacion_3d_mod.RAIZ_REPOSITORIO)


def test_abrir_ventana_3d_sin_token_da_401(contexto) -> None:
    cliente, _, _ = contexto
    respuesta = cliente.post("/simulacion/abrir-ventana-3d", json={"partida_id": "cualquiera"})
    assert respuesta.status_code == 401


def test_abrir_ventana_3d_con_partida_inexistente_da_404(contexto, monkeypatch) -> None:
    cliente, headers, _ = contexto
    monkeypatch.setattr(servicio_simulacion_3d_mod, "PYTHON_SIMULACION", sys.executable)
    llamadas = []
    monkeypatch.setattr(
        servicio_simulacion_3d_mod.subprocess,
        "Popen",
        lambda argumentos, cwd=None: llamadas.append((argumentos, cwd)),
    )

    respuesta = cliente.post(
        "/simulacion/abrir-ventana-3d", json={"partida_id": "no-existe"}, headers=headers
    )

    assert respuesta.status_code == 404
    assert llamadas == []


def test_abrir_ventana_3d_sin_entorno_conda_da_503(contexto, monkeypatch) -> None:
    cliente, headers, _ = contexto
    partida_id = cliente.post("/partida", json={"nivel": 10}, headers=headers).json()["id"]

    monkeypatch.setattr(
        servicio_simulacion_3d_mod, "PYTHON_SIMULACION", r"C:\ruta\que\no\existe\python.exe"
    )
    llamadas = []
    monkeypatch.setattr(
        servicio_simulacion_3d_mod.subprocess,
        "Popen",
        lambda argumentos, cwd=None: llamadas.append((argumentos, cwd)),
    )

    respuesta = cliente.post(
        "/simulacion/abrir-ventana-3d", json={"partida_id": partida_id}, headers=headers
    )

    assert respuesta.status_code == 503
    assert llamadas == []
