from fastapi.testclient import TestClient

from backend.main import app

cliente = TestClient(app)

POSICION_INICIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MATE_EN_UNO = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 3"
FEN_INVALIDO = "esto no es un fen"


def test_healthcheck() -> None:
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_index_sirve_la_pagina_del_frontend() -> None:
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]


def test_jugada_posicion_valida() -> None:
    respuesta = cliente.post("/jugada", json={"fen": POSICION_INICIAL, "nivel": 5})
    assert respuesta.status_code == 200
    assert "jugada" in respuesta.json()


def test_jugada_fen_invalido_devuelve_400() -> None:
    respuesta = cliente.post("/jugada", json={"fen": FEN_INVALIDO, "nivel": 5})
    assert respuesta.status_code == 400


def test_analisis_mate_en_uno() -> None:
    respuesta = cliente.post("/analisis", json={"fen": MATE_EN_UNO, "nivel": 20})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["jugada"] == "Qxf7#"
    assert cuerpo["mate_en"] == 1
