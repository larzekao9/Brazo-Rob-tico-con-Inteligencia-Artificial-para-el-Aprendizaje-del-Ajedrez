"""Tests para endpoint GET /partida con filtrado por rol y usuario."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.rutas.ruta_auth import get_db
from backend.servicios.partida.servicio_partida import crear_partida


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

    # Crear jugador y facilitador (password min_length=6)
    r_jugador = cliente.post("/auth/registro", json={"email": "jugador1@test.com", "nombre": "Jugador 1", "password": "secreto1"})
    token_jugador = r_jugador.json()["tokens"]["access_token"]
    id_jugador = r_jugador.json()["usuario"]["id"]

    r_otro = cliente.post("/auth/registro", json={"email": "jugador2@test.com", "nombre": "Jugador 2", "password": "secreto1"})
    token_otro = r_otro.json()["tokens"]["access_token"]
    id_otro = r_otro.json()["usuario"]["id"]

    r_facil = cliente.post("/auth/registro", json={"email": "profesor@test.com", "nombre": "Profesor", "password": "secreto1", "rol": "facilitador", "clave_facilitador": "admin123"})
    token_facil = r_facil.json()["tokens"]["access_token"]

    try:
        yield cliente, token_jugador, id_jugador, token_otro, id_otro, token_facil
    finally:
        if override_anterior is not None:
            app.dependency_overrides[get_db] = override_anterior
        else:
            app.dependency_overrides.pop(get_db, None)


def test_filtrado_partidas_por_usuario(contexto):
    cliente, token_jugador, id_jugador, token_otro, id_otro, token_facil = contexto

    # Crear partidas en memoria
    p1 = crear_partida(nivel=5, tipo_oponente="motor", usuario_id=id_jugador)
    p2 = crear_partida(nivel=10, tipo_oponente="modelo", usuario_id=id_otro)
    p3 = crear_partida(nivel=8, tipo_oponente="motor", usuario_id=id_otro)
    p3.es_demostracion = True

    # 1. Jugador 1 sólo debe ver su partida (p1) y la de demostración (p3)
    resp = cliente.get("/partida", headers={"Authorization": f"Bearer {token_jugador}"})
    assert resp.status_code == 200
    ids_vistas = [p["id"] for p in resp.json()]
    assert p1.id in ids_vistas
    assert p3.id in ids_vistas
    assert p2.id not in ids_vistas

    # 2. Facilitador debe ver todas (p1, p2, p3)
    resp_facil = cliente.get("/partida", headers={"Authorization": f"Bearer {token_facil}"})
    assert resp_facil.status_code == 200
    ids_facil = [p["id"] for p in resp_facil.json()]
    assert p1.id in ids_facil
    assert p2.id in ids_facil
    assert p3.id in ids_facil

    # 3. Sin token sólo ve demostración (p3)
    resp_anon = cliente.get("/partida")
    assert resp_anon.status_code == 200
    ids_anon = [p["id"] for p in resp_anon.json()]
    assert p3.id in ids_anon
    assert p1.id not in ids_anon
    assert p2.id not in ids_anon
