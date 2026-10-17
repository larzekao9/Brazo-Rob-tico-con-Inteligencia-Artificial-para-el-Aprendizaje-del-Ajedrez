"""Rutas /vision/dataset/*: captura, resumen, borrado y reentrenamiento, sin cámara ni subproceso real."""
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import training.capturar_dataset_propio as capturar
from backend.main import app
from backend.rutas.ruta_auth import get_current_facilitador
from backend.servicios.vision import dataset_propio, piezas

_ESQUINAS = np.array([[150, 80], [750, 40], [780, 620], [120, 660]], dtype=np.int32)
FEN = "8/8/8/8/8/8/8/8"


def _foto():
    imagen = np.full((700, 900, 3), 200, dtype=np.uint8)
    cv2.fillConvexPoly(imagen, _ESQUINAS, (60, 60, 60))
    return imagen


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(capturar, "CARPETA_DATASET", tmp_path)
    monkeypatch.setattr(capturar, "capturar_foto_tablero", _foto)
    app.dependency_overrides[get_current_facilitador] = lambda: 1
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_facilitador, None)


def test_foto_resumen_y_deshacer(cliente) -> None:
    r = cliente.post("/vision/dataset/foto", json={"fen_piezas": FEN})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["guardadas"] == 64 and cuerpo["total"] == 64 and cuerpo["captura_id"].isdigit()
    resumen = cliente.get("/vision/dataset/resumen").json()
    assert resumen == {"por_clase": {"vacia": 64}, "total": 64, "capturas": 1, "minimo_recomendado": 1500}
    control = cliente.get("/vision/dataset/control")
    assert control.status_code == 200 and control.headers["content-type"] == "image/jpeg"
    assert cliente.delete(f"/vision/dataset/captura/{cuerpo['captura_id']}").json() == {"borradas": 64}
    assert cliente.get("/vision/dataset/resumen").json()["total"] == 0


def test_control_sin_imagen_es_404(cliente) -> None:
    assert cliente.get("/vision/dataset/control").status_code == 404


def test_fen_invalido_es_422(cliente) -> None:
    assert cliente.post("/vision/dataset/foto", json={"fen_piezas": "xyz"}).status_code == 422


def test_tablero_no_detectado_es_422(cliente, monkeypatch) -> None:
    def sin_tablero(imagen):
        raise ValueError("No se detectó ningún contorno en la imagen")

    monkeypatch.setattr(capturar, "esquinas_y_margen", sin_tablero)
    assert cliente.post("/vision/dataset/foto", json={"fen_piezas": FEN}).status_code == 422


def test_camara_no_disponible_es_503(cliente, monkeypatch) -> None:
    def falla():
        raise RuntimeError("sin cámara")

    monkeypatch.setattr(capturar, "capturar_foto_tablero", falla)
    assert cliente.post("/vision/dataset/foto", json={"fen_piezas": FEN}).status_code == 503


def test_borrar_con_id_no_numerico_es_422(cliente) -> None:
    assert cliente.delete("/vision/dataset/captura/abc").status_code == 422


def _png(imagen=None) -> bytes:
    ok, buffer = cv2.imencode(".png", _foto() if imagen is None else imagen)
    assert ok
    return buffer.tobytes()


def test_subir_fotos_pieza_guarda_y_cuenta_en_resumen(cliente, tmp_path) -> None:
    pieza = np.full((40, 40, 3), 90, dtype=np.uint8)
    archivos = [("fotos", (f"p{i}.png", _png(pieza), "image/png")) for i in range(3)]
    r = cliente.post("/vision/dataset/pieza", data={"clase": "white-king"}, files=archivos)
    assert r.status_code == 200 and r.json() == {"guardadas": 3, "total_clase": 3}
    assert len(list((tmp_path / "white-king").glob("sub_*.png"))) == 3
    r2 = cliente.post("/vision/dataset/pieza", data={"clase": "white-king"}, files=archivos[:1])
    assert r2.json()["total_clase"] == 4
    assert cliente.get("/vision/dataset/resumen").json()["por_clase"] == {"white-king": 4}


def test_subir_fotos_pieza_clase_invalida_es_422(cliente) -> None:
    archivos = [("fotos", ("p.png", _png(), "image/png"))]
    assert cliente.post("/vision/dataset/pieza", data={"clase": "dragon"}, files=archivos).status_code == 422


def test_subir_fotos_pieza_ilegible_es_422_con_nombre(cliente) -> None:
    archivos = [("fotos", ("ok.png", _png(), "image/png")), ("fotos", ("rota.png", b"no es imagen", "image/png"))]
    r = cliente.post("/vision/dataset/pieza", data={"clase": "vacia"}, files=archivos)
    assert r.status_code == 422 and "rota.png" in r.json()["detail"]


def test_subir_fotos_pieza_mas_de_20_es_422(cliente) -> None:
    archivos = [("fotos", (f"p{i}.png", _png(), "image/png")) for i in range(21)]
    assert cliente.post("/vision/dataset/pieza", data={"clase": "vacia"}, files=archivos).status_code == 422


def test_subir_foto_tablero_guarda_64_casillas_y_control(cliente, monkeypatch) -> None:
    def camara_no_debe_usarse():
        raise AssertionError("no debe usar la cámara")

    monkeypatch.setattr(capturar, "capturar_foto_tablero", camara_no_debe_usarse)
    r = cliente.post(
        "/vision/dataset/foto-tablero",
        data={"fen_piezas": FEN},
        files={"foto": ("t.png", _png(), "image/png")},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["guardadas"] == 64 and cuerpo["total"] == 64 and cuerpo["captura_id"].isdigit()
    assert cliente.get("/vision/dataset/control").status_code == 200


def test_foto_solo_piezas_no_guarda_vacias(cliente) -> None:
    r = cliente.post("/vision/dataset/foto", json={"fen_piezas": "8/8/8/8/8/8/8/R3K3", "solo_piezas": True})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["guardadas"] == 2 and cuerpo["total"] == 2 and cuerpo["captura_id"].isdigit()
    assert cliente.get("/vision/dataset/resumen").json()["por_clase"] == {"white-rook": 1, "white-king": 1}
    assert cliente.get("/vision/dataset/control").status_code == 200


def test_foto_solo_piezas_sin_piezas_es_422(cliente) -> None:
    r = cliente.post("/vision/dataset/foto", json={"fen_piezas": FEN, "solo_piezas": True})
    assert r.status_code == 422
    assert cliente.get("/vision/dataset/resumen").json()["total"] == 0


def test_foto_tablero_solo_piezas(cliente) -> None:
    foto = {"foto": ("t.png", _png(), "image/png")}
    r = cliente.post(
        "/vision/dataset/foto-tablero", data={"fen_piezas": "8/8/8/8/8/8/8/R7", "solo_piezas": "true"}, files=foto
    )
    assert r.status_code == 200 and r.json()["guardadas"] == 1
    assert cliente.get("/vision/dataset/resumen").json()["por_clase"] == {"white-rook": 1}
    vacio = cliente.post(
        "/vision/dataset/foto-tablero", data={"fen_piezas": FEN, "solo_piezas": "true"}, files=foto
    )
    assert vacio.status_code == 422


def test_subir_foto_tablero_errores_422(cliente, monkeypatch) -> None:
    foto = {"foto": ("t.png", _png(), "image/png")}
    assert cliente.post("/vision/dataset/foto-tablero", data={"fen_piezas": "xyz"}, files=foto).status_code == 422
    ilegible = {"foto": ("t.png", b"basura", "image/png")}
    assert cliente.post("/vision/dataset/foto-tablero", data={"fen_piezas": FEN}, files=ilegible).status_code == 422

    def sin_tablero(imagen):
        raise ValueError("No se detectó ningún contorno en la imagen")

    monkeypatch.setattr(capturar, "esquinas_y_margen", sin_tablero)
    assert cliente.post("/vision/dataset/foto-tablero", data={"fen_piezas": FEN}, files=foto).status_code == 422


class _ProcesoFalso:
    def __init__(self, lineas, codigo):
        self.stdout = iter(lineas)
        self._codigo = codigo

    def wait(self):
        return self._codigo


def _esperar(cliente, estado):
    for _ in range(100):
        if cliente.get("/vision/dataset/reentrenar/estado").json()["estado"] == estado:
            return
        time.sleep(0.02)
    pytest.fail(f"no llegó al estado {estado}")


@pytest.fixture
def estado_limpio(monkeypatch):
    monkeypatch.setattr(dataset_propio, "_reentrenamiento", dataset_propio._Reentrenamiento())


def test_reentrenar_con_pocas_muestras_es_400(cliente, estado_limpio) -> None:
    assert cliente.post("/vision/dataset/reentrenar").status_code == 400


def test_reentrenar_exito_invalida_modelo_y_reporta_log(cliente, estado_limpio, monkeypatch) -> None:
    monkeypatch.setattr(dataset_propio, "MINIMO_PARA_REENTRENAR", 10)
    cliente.post("/vision/dataset/foto", json={"fen_piezas": FEN})
    invalidado = []
    monkeypatch.setattr(piezas, "invalidar_modelo", lambda: invalidado.append(True))
    llamadas = []

    def popen(comando, **kwargs):
        llamadas.append((comando, kwargs))
        return _ProcesoFalso(["linea 1\n", "listo\n"], 0)

    monkeypatch.setattr(dataset_propio.subprocess, "Popen", popen)
    r = cliente.post("/vision/dataset/reentrenar")
    assert r.status_code == 200 and r.json() == {"estado": "en_curso"}
    assert llamadas[0][0][1:] == ["-m", "training.reentrenar_con_dataset_propio"]
    assert llamadas[0][1]["env"]["KMP_DUPLICATE_LIB_OK"] == "TRUE"
    _esperar(cliente, "terminado")
    assert cliente.get("/vision/dataset/reentrenar/estado").json()["log"] == "linea 1\nlisto"
    assert invalidado == [True]


def test_reentrenar_409_si_ya_hay_uno_corriendo(cliente, estado_limpio, monkeypatch) -> None:
    monkeypatch.setattr(dataset_propio, "MINIMO_PARA_REENTRENAR", 0)
    monkeypatch.setattr(dataset_propio, "_vigilar", lambda proceso: None)
    monkeypatch.setattr(dataset_propio.subprocess, "Popen", lambda *a, **k: _ProcesoFalso([], 0))
    assert cliente.post("/vision/dataset/reentrenar").status_code == 200
    assert cliente.post("/vision/dataset/reentrenar").status_code == 409


def test_reentrenar_proceso_con_error(cliente, estado_limpio, monkeypatch) -> None:
    monkeypatch.setattr(dataset_propio, "MINIMO_PARA_REENTRENAR", 0)
    monkeypatch.setattr(dataset_propio.subprocess, "Popen", lambda *a, **k: _ProcesoFalso(["boom\n"], 1))
    assert cliente.post("/vision/dataset/reentrenar").status_code == 200
    _esperar(cliente, "error")
    assert "boom" in cliente.get("/vision/dataset/reentrenar/estado").json()["log"]
