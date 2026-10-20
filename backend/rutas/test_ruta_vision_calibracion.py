"""`/vision/calibracion/{estado,previsualizar,guardar,comprobar}` con archivos de esquinas temporales y cámara falsa."""
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rutas import ruta_vision_calibracion
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.vision import tablero

ANCHO, ALTO = 1280, 720
ESQUINAS = {"a1": [400, 600], "h1": [900, 610], "h8": [890, 110], "a8": [410, 100]}


def _foto(desplazamiento: int = 0) -> np.ndarray:
    azar = np.random.default_rng(3)
    imagen = np.full((ALTO, ANCHO, 3), 127, np.uint8)
    for _ in range(250):
        centro = (int(azar.integers(0, ANCHO)), int(azar.integers(0, ALTO)))
        cv2.circle(imagen, centro, int(azar.integers(4, 30)), tuple(int(c) for c in azar.integers(0, 255, 3)), -1)
    if desplazamiento:
        imagen = cv2.warpAffine(imagen, np.float32([[1, 0, desplazamiento], [0, 1, 0]]), (ANCHO, ALTO), borderValue=(127, 127, 127))
    return imagen


def _jpeg(imagen: np.ndarray) -> bytes:
    return cv2.imencode(".png", imagen)[1].tobytes()


@pytest.fixture
def camara(monkeypatch):
    """Cámara falsa: `camara.imagen` es lo que devuelve; `None` simula una cámara sin imagen."""
    estado = type("Camara", (), {"imagen": _foto()})()

    def _capturar():
        if estado.imagen is None:
            raise RuntimeError("sin cámara")
        return estado.imagen

    monkeypatch.setattr(ruta_vision_calibracion, "capturar_foto_tablero", _capturar)
    monkeypatch.setattr(ruta_vision_calibracion, "_fuente_por_defecto", lambda: 0)
    return estado


@pytest.fixture
def cliente(tmp_path, monkeypatch, camara):
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    app.dependency_overrides[get_current_facilitador] = lambda: 1
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_facilitador, None)


def _guardar(cliente, esquinas=ESQUINAS, imagen=None):
    return cliente.post(
        "/vision/calibracion/guardar",
        data={"esquinas": json.dumps(esquinas)},
        files={"foto": ("foto.png", _jpeg(_foto() if imagen is None else imagen), "image/png")},
    )


def test_estado_sin_calibrar(cliente) -> None:
    cuerpo = cliente.get("/vision/calibracion/estado").json()
    assert cuerpo["calibrada"] is False and cuerpo["vigente"] is False and cuerpo["motivo_no_vigente"]


def test_guardar_deja_la_calibracion_vigente_y_compatible_con_la_ruta_vieja(cliente) -> None:
    respuesta = _guardar(cliente)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["calibrada"] is True and cuerpo["vigente"] is True
    assert cuerpo["resolucion"] == [ANCHO, ALTO] and cuerpo["fuente"] == "0" and cuerpo["advertencias"] == []
    assert cliente.get("/vision/calibracion/estado").json()["vigente"] is True
    assert cliente.get("/vision/calibracion").json()["esquinas"]["h1"] == [900.0, 610.0]
    assert tablero.cargar_esquinas_calibradas() is not None


def test_guardar_con_tablero_chico_guarda_y_avisa(cliente) -> None:
    chico = {"a1": [600, 400], "h1": [680, 400], "h8": [680, 330], "a8": [600, 330]}
    respuesta = _guardar(cliente, chico)
    assert respuesta.status_code == 200
    assert any("muy poco de la foto" in a for a in respuesta.json()["advertencias"])


@pytest.mark.parametrize(
    "esquinas",
    [
        {"a1": [400, 600], "h1": [900, 610], "h8": [890, 110]},
        {**ESQUINAS, "h1": [-5, 610]},
        {"a1": [400, 600], "h1": [900, 610], "h8": [410, 110], "a8": [890, 100]},
        {**ESQUINAS, "h1": [5000, 610]},
    ],
)
def test_guardar_invalido_es_422_y_no_guarda(cliente, esquinas) -> None:
    assert _guardar(cliente, esquinas).status_code == 422
    assert cliente.get("/vision/calibracion").json()["calibrada"] is False


def test_guardar_con_esquinas_que_no_son_json_es_422(cliente) -> None:
    respuesta = cliente.post(
        "/vision/calibracion/guardar", data={"esquinas": "no es json"}, files={"foto": ("f.png", _jpeg(_foto()), "image/png")}
    )
    assert respuesta.status_code == 422


def test_guardar_con_foto_ilegible_es_422(cliente) -> None:
    respuesta = cliente.post(
        "/vision/calibracion/guardar", data={"esquinas": json.dumps(ESQUINAS)}, files={"foto": ("f.png", b"basura", "image/png")}
    )
    assert respuesta.status_code == 422


def test_camara_con_otra_resolucion_vence_la_calibracion(cliente, camara) -> None:
    _guardar(cliente)
    camara.imagen = cv2.resize(_foto(), (640, 360))
    cuerpo = cliente.get("/vision/calibracion/estado").json()
    assert cuerpo["calibrada"] is True and cuerpo["vigente"] is False and "640×360" in cuerpo["motivo_no_vigente"]


def test_camara_sin_imagen_deja_vigente_en_null(cliente, camara) -> None:
    _guardar(cliente)
    camara.imagen = None
    cuerpo = cliente.get("/vision/calibracion/estado").json()
    assert cuerpo["calibrada"] is True and cuerpo["vigente"] is None


def test_previsualizar_devuelve_imagen_y_no_guarda(cliente) -> None:
    respuesta = cliente.post(
        "/vision/calibracion/previsualizar",
        data={"esquinas": json.dumps(ESQUINAS)},
        files={"foto": ("f.png", _jpeg(_foto()), "image/png")},
    )
    assert respuesta.status_code == 200 and respuesta.headers["content-type"] == "image/jpeg"
    assert cv2.imdecode(np.frombuffer(respuesta.content, np.uint8), cv2.IMREAD_COLOR) is not None
    assert cliente.get("/vision/calibracion").json()["calibrada"] is False


def test_comprobar_con_la_camara_en_su_lugar(cliente) -> None:
    _guardar(cliente)
    cuerpo = cliente.post("/vision/calibracion/comprobar").json()
    assert cuerpo["movida"] is False


def test_comprobar_avisa_si_la_camara_se_movio(cliente, camara) -> None:
    _guardar(cliente)
    camara.imagen = _foto(desplazamiento=20)
    cuerpo = cliente.post("/vision/calibracion/comprobar").json()
    assert cuerpo["movida"] is True and "volvé a calibrar" in cuerpo["mensaje"]


def test_comprobar_con_foto_subida(cliente) -> None:
    _guardar(cliente)
    respuesta = cliente.post("/vision/calibracion/comprobar", files={"foto": ("f.png", _jpeg(_foto(desplazamiento=20)), "image/png")})
    assert respuesta.status_code == 200 and respuesta.json()["movida"] is True


def test_comprobar_sin_camara_es_503(cliente, camara) -> None:
    camara.imagen = None
    assert cliente.post("/vision/calibracion/comprobar").status_code == 503


def test_sin_token_es_rechazado(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    anonimo = TestClient(app)
    assert anonimo.get("/vision/calibracion/estado").status_code in (401, 403)
    assert anonimo.post("/vision/calibracion/comprobar").status_code in (401, 403)
    assert anonimo.post("/vision/calibracion/guardar", data={"esquinas": "{}"}).status_code in (401, 403)
