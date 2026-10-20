"""Calidad, metadata, vigencia y detección de cámara movida de la calibración (`calibracion_camara.py`)."""
import cv2
import numpy as np
import pytest

from backend.servicios.vision import calibracion_camara as cal
from backend.servicios.vision import tablero

ANCHO, ALTO = 1280, 720
BUENAS = {"a1": (400.0, 600.0), "h1": (900.0, 610.0), "h8": (890.0, 110.0), "a8": (410.0, 100.0)}


@pytest.fixture(autouse=True)
def archivos_temporales(tmp_path, monkeypatch):
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")


def _escena(semilla: int = 0, desplazamiento: tuple[int, int] = (0, 0)) -> np.ndarray:
    """Foto sintética con mucho detalle (círculos y rectángulos al azar), opcionalmente corrida como si la cámara se hubiera movido."""
    azar = np.random.default_rng(semilla)
    imagen = np.full((ALTO, ANCHO, 3), 127, np.uint8)
    for _ in range(250):
        centro = (int(azar.integers(0, ANCHO)), int(azar.integers(0, ALTO)))
        color = tuple(int(c) for c in azar.integers(0, 255, 3))
        if azar.random() < 0.5:
            cv2.circle(imagen, centro, int(azar.integers(4, 30)), color, -1)
        else:
            cv2.rectangle(imagen, centro, (centro[0] + int(azar.integers(6, 50)), centro[1] + int(azar.integers(6, 50))), color, -1)
    if desplazamiento != (0, 0):
        imagen = cv2.warpAffine(imagen, np.float32([[1, 0, desplazamiento[0]], [0, 1, desplazamiento[1]]]), (ANCHO, ALTO), borderValue=(127, 127, 127))
    return imagen


def test_calibracion_buena_no_tiene_advertencias() -> None:
    assert cal.evaluar_calidad(BUENAS, (ANCHO, ALTO)) == []


def test_tablero_muy_chico_avisa() -> None:
    chico = {"a1": (600.0, 400.0), "h1": (680.0, 400.0), "h8": (680.0, 330.0), "a8": (600.0, 330.0)}
    assert any("muy poco de la foto" in a for a in cal.evaluar_calidad(chico, (ANCHO, ALTO)))


def test_tablero_muy_deformado_avisa() -> None:
    aplastado = {"a1": (200.0, 500.0), "h1": (1100.0, 500.0), "h8": (1100.0, 400.0), "a8": (200.0, 400.0)}
    assert any("deformado" in a for a in cal.evaluar_calidad(aplastado, (ANCHO, ALTO)))


def test_lados_opuestos_muy_distintos_avisa() -> None:
    trapecio = {"a1": (200.0, 650.0), "h1": (1000.0, 650.0), "h8": (700.0, 100.0), "a8": (500.0, 100.0)}
    assert any("muy distintos" in a for a in cal.evaluar_calidad(trapecio, (ANCHO, ALTO)))


def test_esquina_pegada_al_borde_avisa() -> None:
    pegada = {**BUENAS, "a1": (3.0, 600.0)}
    assert any("pegada al borde" in a for a in cal.evaluar_calidad(pegada, (ANCHO, ALTO)))


def test_sin_resolucion_no_evalua_tamano_ni_bordes() -> None:
    assert cal.evaluar_calidad({**BUENAS, "a1": (3.0, 600.0)}) == []


def test_estado_sin_calibrar() -> None:
    estado = cal.estado((ANCHO, ALTO), "0")
    assert estado["calibrada"] is False and estado["vigente"] is False and estado["esquinas"] is None


def test_guardar_y_estado_vigente() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    estado = cal.estado((ANCHO, ALTO), "0")
    assert estado["calibrada"] is True and estado["vigente"] is True and estado["motivo_no_vigente"] is None
    assert estado["resolucion"] == [ANCHO, ALTO] and estado["fuente"] == "0" and estado["fecha"]
    assert tablero.cargar_esquinas_calibradas() is not None
    assert cal.ruta_referencia().exists()


def test_otra_resolucion_deja_la_calibracion_vencida() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    estado = cal.estado((640, 480), "0")
    assert estado["calibrada"] is True and estado["vigente"] is False
    assert "640×480" in estado["motivo_no_vigente"] and "1280×720" in estado["motivo_no_vigente"]


def test_otra_camara_deja_la_calibracion_vencida() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    estado = cal.estado((ANCHO, ALTO), "1")
    assert estado["vigente"] is False and "«0»" in estado["motivo_no_vigente"] and "«1»" in estado["motivo_no_vigente"]


def test_camara_sin_imagen_no_se_puede_verificar() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    estado = cal.estado(None, "0")
    assert estado["calibrada"] is True and estado["vigente"] is None


def test_esquinas_guardadas_sin_metadata_no_son_vigentes() -> None:
    tablero.guardar_esquinas_calibradas(BUENAS)
    estado = cal.estado((ANCHO, ALTO), "0")
    assert estado["calibrada"] is True and estado["vigente"] is False and "volvé a calibrar" in estado["motivo_no_vigente"]


def test_metadata_de_otras_esquinas_se_ignora() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    tablero.guardar_esquinas_calibradas({**BUENAS, "h1": (905.0, 610.0)})  # como lo haría la ruta vieja
    assert cal.estado((ANCHO, ALTO), "0")["vigente"] is False


def test_comprobar_sin_calibracion_no_compara() -> None:
    resultado = cal.comprobar_movimiento(_escena())
    assert resultado["movida"] is None and "calibración" in resultado["mensaje"]


def test_comprobar_misma_foto_no_se_movio() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    resultado = cal.comprobar_movimiento(_escena())
    assert resultado["movida"] is False and resultado["desplazamiento_px"] < cal.UMBRAL_DESPLAZAMIENTO_PX


def test_comprobar_camara_corrida_avisa() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    resultado = cal.comprobar_movimiento(_escena(desplazamiento=(18, 12)))
    assert resultado["movida"] is True and resultado["desplazamiento_px"] > cal.UMBRAL_DESPLAZAMIENTO_PX


def test_comprobar_con_otra_resolucion_pide_recalibrar() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    resultado = cal.comprobar_movimiento(cv2.resize(_escena(), (640, 360)))
    assert resultado["movida"] is True and "resolución" in resultado["mensaje"]


def test_comprobar_imagen_lisa_no_se_puede_comparar() -> None:
    cal.guardar_calibracion(BUENAS, _escena(), "0", [])
    resultado = cal.comprobar_movimiento(np.full((ALTO, ANCHO, 3), 100, np.uint8))
    assert resultado["movida"] is None


def test_previsualizar_devuelve_el_tablero_enderezado_con_grilla() -> None:
    vista = cal.previsualizar(_escena(), BUENAS)
    assert vista.shape[0] == vista.shape[1] == tablero.TAMANO_TABLERO_PLANO
