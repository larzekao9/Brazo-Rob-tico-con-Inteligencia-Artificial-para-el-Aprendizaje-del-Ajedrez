"""Modelo de las dos vistas: red, carga del checkpoint, reconocimiento y entrenamiento con datos sintéticos."""
import json

import cv2
import numpy as np
import pytest
import torch

from backend.servicios.vision import piezas, verificacion
from backend.servicios.vision.modelo_piezas import CLASES, RedDosVistas
from backend.servicios.vision.test_geometria3d import _foto_del_tablero


@pytest.fixture
def checkpoint(tmp_path, monkeypatch):
    torch.manual_seed(0)
    red = RedDosVistas(cantidad_clases=len(CLASES), tamano=96)
    ruta = tmp_path / "dos_vistas.pt"
    torch.save({"pesos": red.state_dict(), "clases": CLASES, "tamano": 96, "recorte": "ampliado", "tipo": "dos_vistas", "clases_entrenadas": CLASES}, ruta)
    monkeypatch.setattr(piezas, "RUTA_DOS_VISTAS", ruta)
    piezas.invalidar_modelo()
    yield ruta
    piezas.invalidar_modelo()


def test_la_red_anula_la_vista_que_falta() -> None:
    red = RedDosVistas(cantidad_clases=len(CLASES), tamano=96).eval()
    a, b = torch.rand(2, 3, 96, 96), torch.rand(2, 3, 96, 96)
    solo_a = red(a, b, torch.tensor([[1.0, 0.0]] * 2))
    otra_b = red(a, torch.rand(2, 3, 96, 96), torch.tensor([[1.0, 0.0]] * 2))
    assert torch.allclose(solo_a, otra_b)  # con la máscara en 0 lo que haya en esa vista no influye
    assert not torch.allclose(solo_a, red(a, b, torch.tensor([[1.0, 1.0]] * 2)))


def test_sin_checkpoint_no_hay_modelo_de_dos_vistas(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(piezas, "RUTA_DOS_VISTAS", tmp_path / "no_existe.pt")
    piezas.invalidar_modelo()
    assert piezas.hay_dos_vistas() is False
    with pytest.raises(FileNotFoundError):
        piezas.probabilidades_dos_vistas({"principal": [np.zeros((96, 96, 3), np.uint8)]})


def test_probabilidades_con_una_o_dos_camaras(checkpoint) -> None:
    recortes = [np.random.randint(0, 255, (96, 96, 3), dtype=np.uint8) for _ in range(5)]
    una = piezas.probabilidades_dos_vistas({"principal": recortes})
    dos = piezas.probabilidades_dos_vistas({"principal": recortes, "secundaria": recortes})
    assert una.shape == dos.shape == (5, len(CLASES)) and np.allclose(una.sum(axis=1), 1, atol=1e-5)
    assert piezas.hay_dos_vistas() and piezas.modo_dos_vistas() == "ampliado" and piezas.clases_dos_vistas() == CLASES


def test_el_analisis_usa_el_modelo_de_dos_vistas_cuando_existe(checkpoint, tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import tablero

    imagen, esquinas, _ = _foto_del_tablero()
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    clicks = dict(zip(("a1", "h1", "h8", "a8"), esquinas.tolist()))
    tablero.guardar_esquinas_calibradas(clicks)
    tablero.guardar_esquinas_calibradas(clicks, tablero.archivo_esquinas("secundaria"))
    vista, casillas = verificacion.analizar_camaras({"principal": imagen, "secundaria": imagen})
    assert len(casillas) == 64 and vista.shape[1] == 2 * 800
    vista1, casillas1 = verificacion.analizar_tablero(imagen, "principal")
    assert len(casillas1) == 64 and vista1.shape[1] == 800


def test_entrenar_con_capturas_de_las_dos_camaras(tmp_path, monkeypatch) -> None:
    import training.capturar_dataset_propio as capturar
    import training.entrenar_dos_vistas as entrenamiento
    import training.entrenar_piezas_propio as base

    dataset = tmp_path / "dataset_propio"
    monkeypatch.setattr(capturar, "CARPETA_DATASET", dataset)
    for modulo in (entrenamiento, base):
        monkeypatch.setattr(modulo, "CARPETA_DATASET_PROPIO", dataset)
    monkeypatch.setattr(entrenamiento, "EPOCAS", 1)
    monkeypatch.setattr(entrenamiento, "MINIMO_MUESTRAS", 8)
    monkeypatch.setattr(entrenamiento, "RUTA_DOS_VISTAS", tmp_path / "salida.pt")
    imagen, esquinas, _ = _foto_del_tablero()
    cuadros = capturar.carpeta_cuadros()
    cuadros.mkdir(parents=True)
    etiquetas = {f"{c}{f}": ("vacia" if (c, f) != ("e", "4") else "white-king") for c in "abcdefgh" for f in "12345678"}
    for indice, (camara, marca) in enumerate([("principal", "1000"), ("secundaria", "1001"), ("principal", "2000"), ("secundaria", "2001"), ("principal", "3000")]):
        cv2.imwrite(str(cuadros / f"{marca}.jpg"), imagen)
        grupo = {"1001": "1000", "2001": "2000"}.get(marca, marca)
        (cuadros / f"{marca}.json").write_text(json.dumps({"esquinas": esquinas[::-1].tolist(), "etiquetas": etiquetas, "camara": camara, "grupo": grupo}))
        for casilla, clase in etiquetas.items():
            (dataset / clase).mkdir(parents=True, exist_ok=True)
            (dataset / clase / f"{marca}_{casilla}.png").write_bytes(b"x")  # basta que exista: el recorte sale del cuadro completo
    muestras = entrenamiento.cargar_muestras("ampliado")
    assert len(muestras) == 3 * 64  # tres instantes (el 3º solo con la cámara principal)
    con_dos = [m for m in muestras if len(m["vistas"]) == 2]
    assert len(con_dos) == 2 * 64  # dos instantes con las dos cámaras
    entrenamiento.entrenar("ampliado")
    punto = torch.load(tmp_path / "salida.pt", weights_only=False)
    assert punto["tipo"] == "dos_vistas" and punto["recorte"] == "ampliado" and punto["tamano"] == 96


def test_dibujar_piezas_3d_marca_las_piezas_y_exige_calibracion(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import tablero

    imagen, esquinas, _ = _foto_del_tablero()
    casillas = [{"casilla": "e4", "clase": "white-king", "confianza": 0.95}, {"casilla": "a1", "clase": "vacia", "confianza": 0.99}]
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    with pytest.raises(ValueError):  # sin calibración no hay cajas (falla la calibración o la detección automática)
        verificacion.dibujar_piezas_3d(imagen, "principal", casillas)
    tablero.guardar_esquinas_calibradas(dict(zip(("a1", "h1", "h8", "a8"), esquinas.tolist())))
    dibujada = verificacion.dibujar_piezas_3d(imagen, "principal", casillas)
    assert dibujada.shape[1] <= imagen.shape[1] and dibujada.shape[0] <= imagen.shape[0]  # recortada alrededor del tablero
    assert dibujada.shape[1] > 100 and np.any(dibujada != 0)


def test_un_modelo_de_dos_vistas_entrenado_con_pocas_clases_se_ignora(tmp_path, monkeypatch) -> None:
    red = RedDosVistas(cantidad_clases=len(CLASES), tamano=96)
    ruta = tmp_path / "incompleto.pt"
    torch.save({"pesos": red.state_dict(), "clases": CLASES, "tamano": 96, "recorte": "ampliado", "clases_entrenadas": CLASES[:6]}, ruta)
    monkeypatch.setattr(piezas, "RUTA_DOS_VISTAS", ruta)
    piezas.invalidar_modelo()
    assert piezas.hay_dos_vistas() is False and "6 de 13" in piezas.motivo_dos_vistas_ignorado()
    torch.save({"pesos": red.state_dict(), "clases": CLASES, "tamano": 96, "recorte": "ampliado"}, ruta)  # sin el dato: archivo viejo
    piezas.invalidar_modelo()
    assert piezas.hay_dos_vistas() is False


def test_componer_vista_piezas_elige_plana_cajas_o_ambas(monkeypatch):
    from backend.servicios.vision import verificacion

    plana = np.zeros((100, 100, 3), np.uint8)
    foto = np.zeros((60, 80, 3), np.uint8)
    monkeypatch.setattr(verificacion, "dibujar_piezas_3d", lambda imagen, camara, casillas, **k: np.full((60, 80, 3), 7, np.uint8))
    fotos = {"principal": foto, "secundaria": foto}

    assert verificacion.componer_vista_piezas(plana, fotos, [], "plana").shape == (100, 100, 3)
    assert verificacion.componer_vista_piezas(plana, fotos, [], "cajas").shape == (60, 160, 3)  # las dos cámaras lado a lado
    assert verificacion.componer_vista_piezas(plana, fotos, [], "ambas").shape[1] == 160  # cajas arriba, plana abajo, mismo ancho


def test_componer_vista_piezas_sin_calibrar_vuelve_a_la_plana(monkeypatch):
    from backend.servicios.vision import verificacion

    def _sin_calibrar(*_a, **_k):
        raise ValueError("no calibrada")

    monkeypatch.setattr(verificacion, "dibujar_piezas_3d", _sin_calibrar)
    plana = np.zeros((100, 100, 3), np.uint8)

    assert verificacion.componer_vista_piezas(plana, {"principal": plana}, [], "cajas") is plana
