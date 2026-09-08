import cv2
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.servicios.vision.piezas import RUTA_CHECKPOINT

cliente = TestClient(app)


def _hay_camara_disponible() -> bool:
    camara = cv2.VideoCapture(0)
    disponible = camara.isOpened()
    camara.release()
    return disponible


CAMARA_DISPONIBLE = _hay_camara_disponible()

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


def test_crear_partida_devuelve_posicion_inicial() -> None:
    respuesta = cliente.post("/partida", json={"nivel": 5})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["fen"].startswith(POSICION_INICIAL.split(" ")[0])
    assert cuerpo["terminada"] is False


def test_obtener_partida_inexistente_devuelve_404() -> None:
    respuesta = cliente.get("/partida/no-existe")
    assert respuesta.status_code == 404


def test_mover_partida_responde_con_jugada_del_motor() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}).json()["id"]
    respuesta = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["jugada_motor"] is not None
    assert cuerpo["fen"] != POSICION_INICIAL


def test_mover_partida_jugada_ilegal_devuelve_400() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}).json()["id"]
    respuesta = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e5"})
    assert respuesta.status_code == 400


def test_listar_partidas_incluye_la_recien_creada_con_su_tipo_y_jugadas() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}).json()["id"]
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"})

    respuesta = cliente.get("/partida")
    assert respuesta.status_code == 200
    resumenes = respuesta.json()
    resumen = next(r for r in resumenes if r["id"] == partida_id)
    assert resumen["tipo"] == "digital"
    assert resumen["cantidad_jugadas"] == 2  # la del humano + la respuesta del motor


def test_estado_partida_incluye_las_jugadas_completas() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}).json()["id"]
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"})

    respuesta = cliente.get(f"/partida/{partida_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["jugadas"][0] == "e4"


@pytest.mark.skipif(not CAMARA_DISPONIBLE, reason="No hay cámara conectada en esta máquina")
def test_vision_foto_devuelve_jpeg() -> None:
    respuesta = cliente.get("/vision/foto")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/jpeg"
    assert len(respuesta.content) > 0


@pytest.mark.skipif(not CAMARA_DISPONIBLE, reason="No hay cámara conectada en esta máquina")
@pytest.mark.skipif(not RUTA_CHECKPOINT.exists(), reason="No hay checkpoint entrenado en esta máquina")
def test_vision_reconocer_responde_200_o_422_si_no_ve_tablero() -> None:
    # No depende de que la cámara esté apuntando a un tablero real — solo confirma
    # que el endpoint no rompe: reconoce un tablero válido (200) o avisa que no
    # encontró ninguno en la imagen (422), nunca un error interno sin manejar.
    respuesta = cliente.post("/vision/reconocer", json={"turno": "w"})
    assert respuesta.status_code in (200, 422)
