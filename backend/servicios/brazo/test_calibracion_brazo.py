"""Calibración del brazo: construir, guardar, cargar y rechazar datos mal enseñados."""
import json

import pytest

from backend.servicios.brazo.calibracion_brazo import (
    cargar_calibracion_brazo,
    construir_calibracion,
    guardar_calibracion_brazo,
    puntos_desde_dobotstudio,
)

CERO = (303.8, -1.1, -83.3, 6.1, 16.0, 227.0)
# Tablero de 40 mm por casilla alineado con los ejes, con la herramienta apuntando al tablero (rx, ry, rz fijos).
PUNTOS = {
    "a1": (100.0, 100.0, 20.0, 180.0, 0.0, 90.0),
    "h1": (380.0, 100.0, 20.0, 179.0, 1.0, 91.0),
    "a8": (100.0, 380.0, 20.0, 180.0, -1.0, 89.0),
}


def test_construye_las_64_casillas_y_toma_la_orientacion_de_a1() -> None:
    calibracion = construir_calibracion(CERO, PUNTOS)

    assert calibracion.orientacion == (180.0, 0.0, 90.0) and calibracion.angulos_cero == CERO
    assert len(calibracion.posiciones_casillas) == 64
    assert calibracion.posiciones_casillas["a1"] == pytest.approx((100.0, 100.0, 20.0))
    assert calibracion.posiciones_casillas["e4"] == pytest.approx((100.0 + 4 * 40.0, 100.0 + 3 * 40.0, 20.0))


def test_rechaza_orientaciones_muy_distintas() -> None:
    mal = {**PUNTOS, "h1": (380.0, 100.0, 20.0, 150.0, 0.0, 90.0)}

    with pytest.raises(ValueError, match="orientación"):
        construir_calibracion(CERO, mal)


def test_la_diferencia_de_orientacion_respeta_el_salto_de_180_a_menos_180() -> None:
    cerca_del_salto = {**PUNTOS, "a1": (100.0, 100.0, 20.0, 179.0, 0.0, 90.0), "h1": (380.0, 100.0, 20.0, -179.0, 0.0, 90.0)}

    construir_calibracion(CERO, cerca_del_salto)  # 179 y -179 están a 2° de distancia, no a 358°


def test_rechaza_casillas_o_largos_incorrectos() -> None:
    with pytest.raises(ValueError):
        construir_calibracion(CERO, {k: v for k, v in PUNTOS.items() if k != "a8"})
    with pytest.raises(ValueError):
        construir_calibracion(CERO[:5], PUNTOS)


def test_guarda_y_carga_la_misma_calibracion(tmp_path) -> None:
    ruta = tmp_path / "carpeta" / "brazo.json"

    guardada = guardar_calibracion_brazo(CERO, PUNTOS, ruta)
    cargada = cargar_calibracion_brazo(ruta)

    assert cargada == guardada


def test_sin_archivo_no_hay_calibracion(tmp_path) -> None:
    assert cargar_calibracion_brazo(tmp_path / "no_existe.json") is None


def test_un_archivo_danado_da_error_claro(tmp_path) -> None:
    ruta = tmp_path / "roto.json"
    ruta.write_text(json.dumps({"angulos_cero": [1, 2, 3]}), encoding="utf-8")

    with pytest.raises(ValueError, match="volvé a enseñarlo"):
        cargar_calibracion_brazo(ruta)


def test_el_giro_de_la_muñeca_se_tolera_mas_que_la_inclinacion() -> None:
    con_giro = {**PUNTOS, "h1": (380.0, 100.0, 20.0, 180.0, 0.0, 90.0 + 20.0)}  # 20° de giro: la punta no se mueve

    construir_calibracion(CERO, con_giro)

    with pytest.raises(ValueError, match="orientación"):
        construir_calibracion(CERO, {**PUNTOS, "h1": (380.0, 100.0, 20.0, 180.0, 0.0, 90.0 + 40.0)})


def test_la_inclinacion_de_la_pinza_no_puede_cambiar_mucho() -> None:
    inclinada = {**PUNTOS, "h1": (380.0, 100.0, 20.0, 180.0, 15.0, 90.0)}

    with pytest.raises(ValueError, match="orientación"):
        construir_calibracion(CERO, inclinada)


def test_rechaza_h1_o_a8_enseñadas_muy_por_encima_de_a1() -> None:
    muy_arriba = {**PUNTOS, "h1": (380.0, 100.0, 20.0 + 80.0, 180.0, 0.0, 90.0)}

    with pytest.raises(ValueError, match="por encima de a1"):
        construir_calibracion(CERO, muy_arriba)


def test_la_altura_de_todo_el_tablero_es_la_de_a1_y_h1_o_a8_pueden_estar_mas_arriba_sin_avisos() -> None:
    # Tercera prueba real: a1 apoyada a 236,3 mm; h1 y a8 enseñadas más arriba solo para ubicar X e Y.
    tercera_prueba = {
        "a1": (-108.4, -654.4, 236.3, 177.4, -5.4, -24.5),
        "h1": (112.9, -647.5, 251.9, 176.3, -2.3, -19.8),
        "a8": (-97.6, -446.2, 260.3, -179.8, -0.7, -24.1),
    }

    calibracion = construir_calibracion(CERO, tercera_prueba)

    assert all(z == pytest.approx(236.3) for _, _, z in calibracion.posiciones_casillas.values())
    assert calibracion.avisos == ()
    assert calibracion.posiciones_casillas["a1"][:2] == pytest.approx((-108.4, -654.4))
    assert calibracion.posiciones_casillas["h1"][:2] == pytest.approx((112.9, -647.5))


def test_avisa_si_un_punto_quedo_muy_por_debajo_de_a1() -> None:
    a1_alto = {**PUNTOS, "h1": (380.0, 100.0, 20.0 - 12.0, 180.0, 0.0, 90.0)}

    calibracion = construir_calibracion(CERO, a1_alto)

    assert len(calibracion.avisos) == 1 and "por DEBAJO de a1" in calibracion.avisos[0]


def test_calibracion_real_con_cuatro_puntos_cargados_en_dobotstudio() -> None:
    # Puntos centrados con el jog de DobotStudio Pro (2026-10-16): pinza vertical, misma altura en los cuatro.
    giro = (-180.0, -0.0001, -120.0)
    reales = {
        "a1": (-98.6711, -664.0572, 234.7952, *giro),
        "h1": (117.9582, -666.0572, 234.7952, *giro),
        "h8": (115.5941, -456.1986, 234.7952, *giro),
        "a8": (-94.4421, -453.9149, 234.7952, *giro),
    }

    calibracion = construir_calibracion(CERO, reales)

    assert calibracion.avisos == ()  # ningún punto queda a más de 4 mm de la grilla ajustada
    for casilla, pose in reales.items():
        x, y, _ = calibracion.posiciones_casillas[casilla]
        assert ((x - pose[0]) ** 2 + (y - pose[1]) ** 2) ** 0.5 < 4.0
    paso_columnas = abs(calibracion.posiciones_casillas["b1"][0] - calibracion.posiciones_casillas["a1"][0])
    assert 29.0 < paso_columnas < 32.0  # un tablero de unos 30 mm por casilla


def test_con_cuatro_puntos_el_ajuste_reparte_el_error_de_h8_entre_todos() -> None:
    chico = {**PUNTOS, "h8": (380.0 + 9.0, 380.0, 20.0, 180.0, 0.0, 90.0)}  # h8 medido 9 mm corrido
    grande = {**PUNTOS, "h8": (380.0 + 24.0, 380.0, 20.0, 180.0, 0.0, 90.0)}  # h8 medido 24 mm corrido

    sin_aviso = construir_calibracion(CERO, chico)
    con_aviso = construir_calibracion(CERO, grande)

    assert sin_aviso.avisos == ()  # 9 mm repartidos entre 4 puntos: unos 2 mm cada uno
    assert any("h8" in aviso for aviso in con_aviso.avisos)
    x_h8 = sin_aviso.posiciones_casillas["h8"][0]
    assert 380.0 < x_h8 < 389.0  # h8 queda entre la grilla ideal y el valor medido


def test_h8_es_opcional_pero_no_se_aceptan_casillas_desconocidas() -> None:
    construir_calibracion(CERO, PUNTOS)  # con 3 puntos sigue funcionando

    with pytest.raises(ValueError):
        construir_calibracion(CERO, {**PUNTOS, "e4": (200.0, 200.0, 20.0, 180.0, 0.0, 90.0)})


# --- importación desde DobotStudio Pro (point.json real, descargado el 2026-10-16) -----------------------------------------
POINT_JSON_REAL = [
    {"alias": "A1", "pose": [-98.671066, -664.05719, 234.795227, -179.999985, -0.000064, -120], "name": "P1", "tool": 0, "user": 0,
     "joint": [274.25354, -32.061214, -86.55304, 28.595221, 90.503593, -56.388229]},
    {"alias": "H1", "pose": [117.958199, -666.05719, 234.795227, -179.999985, -0.000064, -120], "name": "P2", "tool": 0, "user": 0,
     "joint": [292.649902, -32.675663, -85.493935, 28.150528, 90.510834, -37.98753]},
    {"alias": "H8", "pose": [115.594124, -456.198578, 234.795227, -179.999985, -0.000064, -120], "name": "P3", "tool": 0, "user": 0,
     "joint": [302.435913, -8.164964, -122.173439, 40.320778, 90.193253, -28.313505]},
    {"alias": "A8", "pose": [-94.442062, -453.914886, 234.795227, -179.999985, -0.000064, -120], "name": "P4", "tool": 0, "user": 0,
     "joint": [276.741943, -7.273008, -123.247467, 40.502945, 90.18103, -54.009048]},
    {"alias": "DESCANSO", "pose": [-3.548397, -262.353455, 234.795227, -179.999985, -0.000064, -120], "name": "P5", "tool": 0, "user": 0,
     "joint": [302.85675, 28.206139, -149.123886, 30.902992, 89.710472, -27.810482]},
]


def _archivo_dobotstudio(tmp_path, registros) -> "Path":
    ruta = tmp_path / "point.json"
    ruta.write_text(json.dumps(registros), encoding="utf-8")
    return ruta


def test_importa_el_point_json_real_de_dobotstudio(tmp_path) -> None:
    angulos_cero, puntos = puntos_desde_dobotstudio(_archivo_dobotstudio(tmp_path, POINT_JSON_REAL))

    assert angulos_cero == pytest.approx((302.85675, 28.206139, -149.123886, 30.902992, 89.710472, -27.810482))
    assert set(puntos) == {"a1", "h1", "h8", "a8"} and puntos["a1"][:3] == pytest.approx((-98.671066, -664.05719, 234.795227))
    calibracion = construir_calibracion(angulos_cero, puntos)
    assert calibracion.avisos == () and calibracion.angulos_cero == pytest.approx(angulos_cero)


def test_los_alias_no_distinguen_mayusculas(tmp_path) -> None:
    minusculas = [{**r, "alias": r["alias"].lower()} for r in POINT_JSON_REAL]

    _, puntos = puntos_desde_dobotstudio(_archivo_dobotstudio(tmp_path, minusculas))

    assert set(puntos) == {"a1", "h1", "h8", "a8"}


def test_h8_es_opcional_en_la_importacion(tmp_path) -> None:
    sin_h8 = [r for r in POINT_JSON_REAL if r["alias"] != "H8"]

    _, puntos = puntos_desde_dobotstudio(_archivo_dobotstudio(tmp_path, sin_h8))

    assert set(puntos) == {"a1", "h1", "a8"}


def test_falta_un_punto_necesario(tmp_path) -> None:
    sin_descanso = [r for r in POINT_JSON_REAL if r["alias"] != "DESCANSO"]

    with pytest.raises(ValueError, match="DESCANSO"):
        puntos_desde_dobotstudio(_archivo_dobotstudio(tmp_path, sin_descanso))


def test_rechaza_puntos_con_otra_herramienta_o_usuario(tmp_path) -> None:
    con_tool = [{**r, "tool": 1} if r["alias"] == "A1" else r for r in POINT_JSON_REAL]

    with pytest.raises(ValueError, match="tool=1"):
        puntos_desde_dobotstudio(_archivo_dobotstudio(tmp_path, con_tool))


def test_un_archivo_que_no_es_de_dobotstudio_da_error_claro(tmp_path) -> None:
    ruta = tmp_path / "otro.json"
    ruta.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="DobotStudio"):
        puntos_desde_dobotstudio(ruta)
