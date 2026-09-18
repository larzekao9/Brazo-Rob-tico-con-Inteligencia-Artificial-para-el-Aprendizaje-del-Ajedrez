import uuid

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.rutas.ruta_auth import get_db
from backend.servicios.vision.piezas import RUTA_CHECKPOINT

# `POST /partida` y `GET /partida/{id}` exigen `Authorization: Bearer <token>`
# (HU10), que a su vez necesita una base de datos real detrás de `get_db` —
# se apunta a una SQLite en memoria para no requerir Postgres solo para
# correr estos tests, igual que en `backend/rutas/test_ruta_auth.py`.
_engine_auth_test = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
crear_tablas(_engine_auth_test)
_fabrica_sesiones_test = crear_fabrica_sesiones(_engine_auth_test)


def _get_db_test():
    sesion = _fabrica_sesiones_test()
    try:
        yield sesion
    finally:
        sesion.close()


app.dependency_overrides[get_db] = _get_db_test

cliente = TestClient(app)


def _headers_usuario_nuevo() -> dict[str, str]:
    """Registra un jugador con email único y devuelve su header Authorization."""
    email = f"{uuid.uuid4().hex}@test.com"
    respuesta = cliente.post(
        "/auth/registro", json={"email": email, "nombre": "Jugador de prueba", "password": "secreto1"}
    )
    token = respuesta.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
    respuesta = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo())
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["fen"].startswith(POSICION_INICIAL.split(" ")[0])
    assert cuerpo["terminada"] is False


def test_crear_partida_sin_token_devuelve_401() -> None:
    respuesta = cliente.post("/partida", json={"nivel": 5})
    assert respuesta.status_code == 401


def test_obtener_partida_inexistente_devuelve_404() -> None:
    respuesta = cliente.get("/partida/no-existe", headers=_headers_usuario_nuevo())
    assert respuesta.status_code == 404


def test_obtener_partida_sin_token_devuelve_401() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo()).json()["id"]
    respuesta = cliente.get(f"/partida/{partida_id}")
    assert respuesta.status_code == 401


def test_obtener_partida_de_otro_usuario_devuelve_403() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo()).json()["id"]

    respuesta = cliente.get(f"/partida/{partida_id}", headers=_headers_usuario_nuevo())

    assert respuesta.status_code == 403


def test_obtener_partida_propia_devuelve_200() -> None:
    headers = _headers_usuario_nuevo()
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=headers).json()["id"]

    respuesta = cliente.get(f"/partida/{partida_id}", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == partida_id


def test_crear_partida_con_fen_inicial_arranca_ahi() -> None:
    # Simula el botón "Usar esta posición" tras POST /vision/reconocer.
    fen_escaneado = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    respuesta = cliente.post(
        "/partida", json={"nivel": 5, "fen_inicial": fen_escaneado}, headers=_headers_usuario_nuevo()
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["fen"] == fen_escaneado
    assert cuerpo["jugadas"] == []


def test_crear_partida_con_fen_inicial_invalido_devuelve_400() -> None:
    respuesta = cliente.post(
        "/partida", json={"nivel": 5, "fen_inicial": "esto no es un fen"}, headers=_headers_usuario_nuevo()
    )
    assert respuesta.status_code == 400


def test_crear_partida_con_tipo_oponente_no_soportado_devuelve_400() -> None:
    respuesta = cliente.post(
        "/partida", json={"nivel": 5, "tipo_oponente": "participante"}, headers=_headers_usuario_nuevo()
    )
    assert respuesta.status_code == 400


def test_mover_partida_responde_con_jugada_del_motor() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo()).json()["id"]
    respuesta = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["jugada_motor"] is not None
    assert cuerpo["fen"] != POSICION_INICIAL


def test_mover_partida_jugada_ilegal_devuelve_400() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo()).json()["id"]
    respuesta = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e5"})
    assert respuesta.status_code == 400


def test_listar_partidas_incluye_la_recien_creada_con_su_tipo_y_jugadas() -> None:
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo()).json()["id"]
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"})

    respuesta = cliente.get("/partida")
    assert respuesta.status_code == 200
    resumenes = respuesta.json()
    resumen = next(r for r in resumenes if r["id"] == partida_id)
    assert resumen["tipo"] == "digital"
    assert resumen["cantidad_jugadas"] == 2  # la del humano + la respuesta del motor


def test_estado_partida_incluye_las_jugadas_completas() -> None:
    headers = _headers_usuario_nuevo()
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=headers).json()["id"]
    cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "e2e4"})

    respuesta = cliente.get(f"/partida/{partida_id}", headers=headers)
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
    respuesta = cliente.post("/vision/reconocer", data={"turno": "w"})
    assert respuesta.status_code in (200, 422)


def test_vision_reconocer_con_foto_subida_sin_tablero_devuelve_422() -> None:
    # Una imagen sin ningún tablero — confirma que la ruta de "foto subida"
    # (en vez de la cámara fija) procesa el archivo. No necesita cámara ni
    # checkpoint entrenado: falla antes, al no encontrar las 4 esquinas.
    imagen = np.full((200, 200, 3), 128, dtype=np.uint8)
    exito, buffer = cv2.imencode(".jpg", imagen)
    assert exito
    respuesta = cliente.post(
        "/vision/reconocer",
        data={"turno": "w"},
        files={"foto_subida": ("foto.jpg", buffer.tobytes(), "image/jpeg")},
    )
    assert respuesta.status_code == 422


@pytest.mark.skipif(not CAMARA_DISPONIBLE, reason="No hay cámara conectada en esta máquina")
@pytest.mark.skipif(not RUTA_CHECKPOINT.exists(), reason="No hay checkpoint entrenado en esta máquina")
def test_mover_desde_foto_responde_200_o_422_si_no_coincide_ninguna_jugada() -> None:
    # No depende de que la cámara esté apuntando a un tablero físico real en la
    # posición inicial — solo confirma que el endpoint no rompe con un error
    # interno sin manejar, sea que detecte una jugada válida (200) o no (422).
    partida_id = cliente.post("/partida", json={"nivel": 5}, headers=_headers_usuario_nuevo()).json()["id"]
    respuesta = cliente.post(f"/partida/{partida_id}/mover-desde-foto")
    assert respuesta.status_code in (200, 422)
