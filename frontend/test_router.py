"""Tests del router del frontend: valida que la plantilla renderiza correctamente."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from frontend.router import router, static_files


def crear_app_prueba() -> FastAPI:
    """Construye una app FastAPI mínima solo con el router del frontend."""
    app = FastAPI()
    app.include_router(router)
    app.mount("/static", static_files, name="static")
    return app


def test_index_responde_200() -> None:
    cliente = TestClient(crear_app_prueba())
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200


def test_index_contiene_boton_calcular_jugada() -> None:
    cliente = TestClient(crear_app_prueba())
    respuesta = cliente.get("/")
    assert "Calcular jugada" in respuesta.text


def test_index_incluye_fen_inicial_por_defecto() -> None:
    cliente = TestClient(crear_app_prueba())
    respuesta = cliente.get("/")
    assert "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR" in respuesta.text
