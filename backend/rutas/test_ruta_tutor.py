"""Rutas /tutor (tutor conversacional "Turing") contra una SQLite en memoria —
sin Postgres y sin pegarle nunca a la red real de Groq: `_llamar_api_groq`
queda monkeypatcheada en cada test que la necesita (mismo patrón que
`test_ruta_facilitador.py`).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.repositorios.repositorio_tutor import RepositorioTutorEnMemoria
from backend.rutas.ruta_auth import get_db
from backend.servicios.tutor import servicio_tutor
from backend.servicios.tutor.servicio_tutor import TutorNoDisponibleError


@pytest.fixture
def cliente(monkeypatch):
    # Repositorio del tutor aislado por test: es un singleton módulo-level
    # (mismo patrón que `servicio_partida._repositorio`), y sin esto el
    # historial de un test se filtraría al siguiente si dos tests registran
    # un usuario con el mismo id autoincremental en su propia SQLite fresca.
    monkeypatch.setattr(servicio_tutor, "_repositorio", RepositorioTutorEnMemoria())

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
    try:
        yield TestClient(app)
    finally:
        if override_anterior is not None:
            app.dependency_overrides[get_db] = override_anterior
        else:
            app.dependency_overrides.pop(get_db, None)


JUGADOR = {"email": "tutor-ruta@test.com", "nombre": "Jugador Tutor", "password": "secreto1"}


def _token(cliente) -> str:
    return cliente.post("/auth/registro", json=JUGADOR).json()["tokens"]["access_token"]


class _MensajeFalso:
    """Imita `response.choices[0].message` del SDK `openai` (forma de la Chat
    Completions API) sin tool_calls pendientes."""

    def __init__(self, texto: str) -> None:
        self.content = texto
        self.tool_calls = None


class _RespuestaFalsa:
    def __init__(self, texto: str) -> None:
        from types import SimpleNamespace

        self.choices = [SimpleNamespace(message=_MensajeFalso(texto))]


def _mock_respuesta_directa(texto: str):
    """`_llamar_api_groq` falsa que responde texto final sin pedir ninguna tool."""

    def _falso(mensajes: list[dict], tools: list[dict]):
        return _RespuestaFalsa(texto)

    return _falso


def test_post_mensaje_y_get_historial_persiste_dos_turnos(cliente, monkeypatch) -> None:
    monkeypatch.setattr(servicio_tutor, "_llamar_api_groq", _mock_respuesta_directa("Hola, soy Turing."))
    headers = {"Authorization": f"Bearer {_token(cliente)}"}

    respuesta = cliente.post("/tutor/mensaje", json={"mensaje": "Hola"}, headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["respuesta"] == "Hola, soy Turing."
    assert cuerpo["creado_en"]

    historial = cliente.get("/tutor/historial", headers=headers)
    assert historial.status_code == 200
    turnos = historial.json()["turnos"]
    assert len(turnos) == 2
    assert turnos[0]["rol"] == "user"
    assert turnos[0]["contenido"] == "Hola"
    assert turnos[1]["rol"] == "assistant"
    assert turnos[1]["contenido"] == "Hola, soy Turing."


def test_get_historial_sin_nada_enviado_da_vacio(cliente) -> None:
    headers = {"Authorization": f"Bearer {_token(cliente)}"}

    respuesta = cliente.get("/tutor/historial", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["turnos"] == []


def test_post_mensaje_sin_token_da_401(cliente) -> None:
    respuesta = cliente.post("/tutor/mensaje", json={"mensaje": "Hola"})
    assert respuesta.status_code == 401


def test_delete_historial_y_luego_get_da_vacio(cliente, monkeypatch) -> None:
    monkeypatch.setattr(servicio_tutor, "_llamar_api_groq", _mock_respuesta_directa("Respuesta cualquiera."))
    headers = {"Authorization": f"Bearer {_token(cliente)}"}
    cliente.post("/tutor/mensaje", json={"mensaje": "Hola"}, headers=headers)

    borrado = cliente.delete("/tutor/historial", headers=headers)
    assert borrado.status_code == 204

    historial = cliente.get("/tutor/historial", headers=headers)
    assert historial.json()["turnos"] == []


def test_post_mensaje_con_api_de_groq_fallando_da_503_y_conserva_el_turno_del_usuario(
    cliente, monkeypatch
) -> None:
    def _falla(mensajes: list[dict], tools: list[dict]):
        raise TutorNoDisponibleError("GROQ_API_KEY inválida o red caída")

    monkeypatch.setattr(servicio_tutor, "_llamar_api_groq", _falla)
    headers = {"Authorization": f"Bearer {_token(cliente)}"}

    respuesta = cliente.post(
        "/tutor/mensaje", json={"mensaje": "¿Cómo se mueve el rey?"}, headers=headers
    )

    assert respuesta.status_code == 503

    historial = cliente.get("/tutor/historial", headers=headers)
    turnos = historial.json()["turnos"]
    assert len(turnos) == 1
    assert turnos[0]["rol"] == "user"
    assert turnos[0]["contenido"] == "¿Cómo se mueve el rey?"
