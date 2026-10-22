import math

import cv2
import numpy as np
import pytest

from backend.servicios.vision import geometria3d as g

ANCHO, ALTO = 1280, 720
LENTE_REAL = g.lente_supuesto(ANCHO, ALTO, 80.0)


def _rotacion_mirando_al_centro(posicion: np.ndarray, destino: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pose cámara->tablero de una cámara en `posicion` (mm, coordenadas del tablero) que mira a `destino`."""
    z = destino - posicion
    z = z / np.linalg.norm(z)
    x = np.cross(z, [0.0, 0.0, 1.0]) if abs(z[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    rotacion = np.stack([x, y, z])  # filas = ejes de la cámara en el tablero
    rvec, _ = cv2.Rodrigues(rotacion)
    return rvec, (-rotacion @ posicion).reshape(3, 1)


def _foto_del_tablero(posicion=(120.0, -250.0, 420.0)) -> tuple[np.ndarray, np.ndarray, tuple]:
    """Imagen sintética de un damero 8x8 visto desde `posicion` con el lente real, y las esquinas a1 h1 h8 a8 en ella."""
    centro = np.array([g.LADO_TABLERO_MM / 2, g.LADO_TABLERO_MM / 2, 0.0])
    rvec, tvec = _rotacion_mirando_al_centro(np.array(posicion), centro)
    px_por_mm = 6
    lado = int(g.LADO_TABLERO_MM * px_por_mm)
    plano = np.full((lado + 200, lado + 200, 3), 235, np.uint8)
    paso = lado // 8
    for fila in range(8):
        for col in range(8):
            if (fila + col) % 2 == 0:
                plano[100 + fila * paso : 100 + (fila + 1) * paso, 100 + col * paso : 100 + (col + 1) * paso] = 20
    # homografía plano(px) -> imagen, a partir de 4 puntos del tablero proyectados con la pose real
    origen = np.float32([[100, 100 + lado], [100 + lado, 100 + lado], [100 + lado, 100], [100, 100]])  # a1 h1 h8 a8 en el plano (Y hacia arriba)
    esquinas = g.proyectar(g.CORNERS_TABLERO_MM, rvec, tvec, LENTE_REAL).astype(np.float32)
    homografia = cv2.getPerspectiveTransform(origen, esquinas)
    imagen = cv2.warpPerspective(plano, homografia, (ANCHO, ALTO), borderValue=(200, 200, 200))
    return imagen, esquinas, (rvec, tvec)


def test_pose_recupera_la_posicion_de_la_camara() -> None:
    _, esquinas, _ = _foto_del_tablero()
    info = g.diagnostico(esquinas, LENTE_REAL)
    assert info["posicion_mm"] == pytest.approx([120, -250, 420], abs=2) and info["error_px"] < 0.1
    assert 30 < info["inclinacion_grados"] < 60


def test_esquinas_espejadas_se_rechazan_o_dan_error_grande() -> None:
    _, esquinas, _ = _foto_del_tablero()
    espejadas = esquinas[[0, 3, 2, 1]]  # a1 a8 h8 h1: otro orden
    try:
        info = g.diagnostico(espejadas, LENTE_REAL)
        assert info["error_px"] > 5 or info["altura_mm"] < 0
    except ValueError:
        pass


def test_recortes_por_volumen_son_cuadrados_y_siguen_a_la_pieza_alta() -> None:
    imagen, esquinas, (rvec, tvec) = _foto_del_tablero()
    recortes = g.recortes_volumen(imagen, esquinas, LENTE_REAL)
    assert len(recortes) == 64 and all(r.shape == (96, 96, 3) for r in recortes.values())
    cajas = g.cajas_proyectadas(esquinas, LENTE_REAL)
    # la tapa de la caja (z = 60 mm) queda más alta en la imagen que la base: el recorte la contiene entera
    base, tapa = cajas["e4"][:4], cajas["e4"][4:]
    assert tapa[:, 1].min() < base[:, 1].min() - 5


def test_autocalibrar_recupera_la_focal_con_varias_vistas() -> None:
    imagenes = []
    for posicion in [(120, -250, 420), (300, -150, 380), (-60, -200, 360), (120, 500, 400)]:
        imagen, _, _ = _foto_del_tablero(posicion)
        imagenes.append(imagen)
    lente, avisos = g.autocalibrar_lente(imagenes, "principal")
    assert lente.origen == "autocalibrado", avisos
    assert lente.fx == pytest.approx(LENTE_REAL.fx, rel=0.12)


def test_autocalibrar_sin_tablero_visible_da_error_claro() -> None:
    with pytest.raises(ValueError, match="esquinas internas"):
        g.autocalibrar_lente([np.full((ALTO, ANCHO, 3), 120, np.uint8)])


def test_el_lente_se_guarda_por_camara_y_resolucion(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import tablero

    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    lente = g.Lente(ANCHO, ALTO, 900.0, 900.0, ANCHO / 2, ALTO / 2, origen="autocalibrado", fotos=4)
    g.guardar_lente(lente, "secundaria")
    assert g.cargar_lente("secundaria", ANCHO, ALTO).fx == 900.0
    assert g.cargar_lente("secundaria", 1920, 1080).origen == "supuesto"  # otra resolución: no vale
    assert g.cargar_lente("principal", ANCHO, ALTO).origen == "supuesto"
    g.borrar_lente("secundaria")
    assert g.cargar_lente("secundaria", ANCHO, ALTO).origen == "supuesto"


def test_la_huella_de_la_base_es_mas_chica_que_la_caja_completa() -> None:
    imagen, esquinas, _ = _foto_del_tablero()
    base = g.cajas_proyectadas(esquinas, LENTE_REAL, g.ALTURA_BASE_MM)["e4"]
    caja = g.cajas_proyectadas(esquinas, LENTE_REAL, g.ALTURA_PIEZA_MM)["e4"]
    assert np.ptp(base[:, 1]) < np.ptp(caja[:, 1])  # la huella (8 mm) ocupa menos alto en la imagen que la caja de 60 mm
    recortes = g.recortes_base(imagen, esquinas, LENTE_REAL)
    assert len(recortes) == 64 and all(r.shape == (64, 64, 3) for r in recortes.values())


def test_ocupacion_por_la_base_usa_la_huella_cuando_el_modelo_lo_pide(monkeypatch, tmp_path) -> None:
    from backend.servicios.vision import captura_estable, ocupacion, tablero

    imagen, esquinas, _ = _foto_del_tablero()
    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    tablero.guardar_esquinas_calibradas(dict(zip(("a1", "h1", "h8", "a8"), esquinas.tolist())))
    vistos = []

    def falso(recortes):
        vistos.append(recortes)
        return np.tile([1.0, 0.0, 0.0], (len(recortes), 1))

    monkeypatch.setattr(ocupacion, "clasificar_ocupacion", falso)
    monkeypatch.setattr(ocupacion, "modo_recorte", lambda: "base")
    probs = captura_estable.ocupacion_de_imagen(imagen, "principal")
    assert probs.shape == (64, 3) and len(vistos[0]) == 64 and vistos[0][0].shape == (64, 64, 3)  # huella de 64x64
    assert ocupacion.tensor_de_recorte(np.zeros((64, 64, 3), np.uint8), "base").shape == (3, 64, 64)
