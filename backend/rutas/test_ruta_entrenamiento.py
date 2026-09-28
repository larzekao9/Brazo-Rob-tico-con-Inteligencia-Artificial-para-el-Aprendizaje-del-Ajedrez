"""Rutas /entrenamiento (HU4, base): solo facilitador."""
import io
import zipfile
from datetime import datetime, timezone

import chess
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.modelos.tablas_orm import JugadaORM, PartidaORM
from backend.rutas.ruta_auth import get_db

JUGADOR = {"email": "jugadora-ent@test.com", "nombre": "Jugadora", "password": "secreto1"}
FACILITADOR = {"email": "profe-ent@test.com", "nombre": "Profe", "password": "secreto1", "rol": "facilitador"}

_RUY_LOPEZ = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]


@pytest.fixture
def contexto(monkeypatch):
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

    headers_jugador = {}
    respuesta_jugador = cliente.post("/auth/registro", json=JUGADOR)
    headers_jugador = {"Authorization": f"Bearer {respuesta_jugador.json()['tokens']['access_token']}"}
    usuario_jugador_id = respuesta_jugador.json()["usuario"]["id"]

    respuesta_facilitador = cliente.post("/auth/registro", json=FACILITADOR)
    headers_facilitador = {"Authorization": f"Bearer {respuesta_facilitador.json()['tokens']['access_token']}"}

    try:
        yield cliente, headers_jugador, headers_facilitador, usuario_jugador_id, fabrica
    finally:
        if override_anterior is not None:
            app.dependency_overrides[get_db] = override_anterior
        else:
            app.dependency_overrides.pop(get_db, None)


def _insertar_partida_valida(fabrica, usuario_id: int, partida_id: str) -> None:
    tablero = chess.Board()
    with fabrica() as sesion:
        fila = PartidaORM(
            id=partida_id,
            usuario_id=usuario_id,
            fecha=datetime.now(timezone.utc).replace(tzinfo=None),
            resultado="1-0",
            tipo="digital",
            fen=chess.STARTING_FEN,
            fen_inicial=chess.STARTING_FEN,
            nivel=10,
            tipo_oponente="motor",
            jugadas_uci="",
            estado="terminada",
        )
        sesion.add(fila)
        jugadas_uci = []
        for numero, jugada_san in enumerate(_RUY_LOPEZ, start=1):
            movimiento = tablero.parse_san(jugada_san)
            sesion.add(
                JugadaORM(
                    partida_id=partida_id,
                    numero=numero,
                    fen_antes=tablero.fen(),
                    movimiento=movimiento.uci(),
                    decidido_por="jugador" if numero % 2 == 1 else "motor",
                )
            )
            jugadas_uci.append(movimiento.uci())
            tablero.push(movimiento)
        fila.fen = tablero.fen()
        fila.jugadas_uci = " ".join(jugadas_uci)
        sesion.commit()


def test_estado_sin_token_da_401(contexto) -> None:
    cliente, _, _, _, _ = contexto
    assert cliente.get("/entrenamiento/estado").status_code == 401


def test_estado_con_jugador_da_403(contexto) -> None:
    cliente, headers_jugador, _, _, _ = contexto
    respuesta = cliente.get("/entrenamiento/estado", headers=headers_jugador)
    assert respuesta.status_code == 403


def test_estado_con_facilitador_da_200_con_el_contrato_esperado(contexto) -> None:
    cliente, _, headers_facilitador, _, _ = contexto
    respuesta = cliente.get("/entrenamiento/estado", headers=headers_facilitador)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo.keys()) == {
        "umbral_partidas", "minimo_jugadas_por_partida", "partidas_validas_total", "partidas_nuevas",
        "jugadas_jugador_nuevas", "progreso", "listo_para_entrenar", "ultima_descarga", "modelo_actual",
    }
    assert cuerpo["minimo_jugadas_por_partida"] == 5
    assert cuerpo["ultima_descarga"] is None


def test_dataset_con_jugador_da_403(contexto) -> None:
    cliente, headers_jugador, _, _, _ = contexto
    respuesta = cliente.post("/entrenamiento/dataset", json={}, headers=headers_jugador)
    assert respuesta.status_code == 403


def test_dataset_sin_partidas_da_409(contexto) -> None:
    cliente, _, headers_facilitador, _, _ = contexto
    respuesta = cliente.post("/entrenamiento/dataset", json={}, headers=headers_facilitador)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]


def test_dataset_con_partidas_devuelve_zip_descargable(contexto) -> None:
    cliente, _, headers_facilitador, usuario_jugador_id, fabrica = contexto
    _insertar_partida_valida(fabrica, usuario_jugador_id, "partida-1")

    respuesta = cliente.post("/entrenamiento/dataset", json={"solo_nuevas": False}, headers=headers_facilitador)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/zip"
    disposicion = respuesta.headers["content-disposition"]
    assert "attachment" in disposicion and ".zip" in disposicion

    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as zip_archivo:
        assert set(zip_archivo.namelist()) == {
            "partidas.pgn", "jugadas.csv", "partidas.csv", "manifiesto.json", "LEEME.txt",
        }


def test_dataset_default_solo_nuevas_false(contexto) -> None:
    cliente, _, headers_facilitador, usuario_jugador_id, fabrica = contexto
    _insertar_partida_valida(fabrica, usuario_jugador_id, "partida-1")

    respuesta = cliente.post("/entrenamiento/dataset", json={}, headers=headers_facilitador)

    assert respuesta.status_code == 200
