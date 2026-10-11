"""POST /partida/{id}/tiempo-agotado: el reloj de la pantalla termina la partida (SQLite en memoria)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.rutas.ruta_auth import get_db


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

    anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _db
    cliente = TestClient(app)

    def registrar(email: str) -> dict:
        respuesta = cliente.post("/auth/registro", json={"email": email, "nombre": "Jugador", "password": "secreto1"})
        return {"Authorization": f"Bearer {respuesta.json()['tokens']['access_token']}"}

    try:
        yield cliente, registrar
    finally:
        if anterior is not None:
            app.dependency_overrides[get_db] = anterior
        else:
            app.dependency_overrides.pop(get_db, None)


def _partida_con_una_jugada(cliente, headers) -> str:
    partida_id = cliente.post("/partida", json={"nivel": 3}, headers=headers).json()["id"]
    assert cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"}, headers=headers).status_code == 200
    return partida_id


def test_tiempo_agotado_sin_token_da_401(contexto) -> None:
    cliente, _ = contexto
    assert cliente.post("/partida/x/tiempo-agotado", json={"lado": "blancas"}).status_code == 401


def test_tiempo_agotado_de_otro_usuario_da_403(contexto) -> None:
    cliente, registrar = contexto
    dueno = registrar("dueno@test.com")
    intruso = registrar("intruso@test.com")
    partida_id = _partida_con_una_jugada(cliente, dueno)

    assert cliente.post(f"/partida/{partida_id}/tiempo-agotado", json={"lado": "blancas"}, headers=intruso).status_code == 403


def test_tiempo_agotado_del_dueno_termina_la_partida_como_derrota(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("dueno@test.com")
    partida_id = _partida_con_una_jugada(cliente, headers)

    respuesta = cliente.post(f"/partida/{partida_id}/tiempo-agotado", json={"lado": "blancas"}, headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["terminada"] is True and cuerpo["resultado"] == "0-1" and cuerpo["estado"] == "terminada"
    # Ya no acepta más jugadas.
    assert cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "d2d4"}, headers=headers).status_code == 400


def test_tiempo_agotado_sin_jugadas_o_con_lado_invalido_da_400(contexto) -> None:
    cliente, registrar = contexto
    headers = registrar("dueno@test.com")
    sin_jugadas = cliente.post("/partida", json={"nivel": 3}, headers=headers).json()["id"]
    assert cliente.post(f"/partida/{sin_jugadas}/tiempo-agotado", json={"lado": "blancas"}, headers=headers).status_code == 400

    partida_id = _partida_con_una_jugada(cliente, headers)
    assert cliente.post(f"/partida/{partida_id}/tiempo-agotado", json={"lado": "verdes"}, headers=headers).status_code == 400
