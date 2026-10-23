"""Validación geométrica de poses del CR5AS: límites, mesa, tablero y choques entre eslabones."""
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from backend.servicios.brazo import geometria_brazo as g

URDF = Path(__file__).resolve().parents[1] / "simulacion" / "assets" / "dobot_cr5as" / "dobot_cr5as.urdf"
DESCANSO = [302.85675, 28.206139, -149.123886, 30.902992, 89.710472, -27.810482]  # la «posición cero» calibrada del brazo real
Z_TOPE = 223.65


def test_las_medidas_son_las_del_urdf_del_cr5as() -> None:
    juntas = [j for j in ET.parse(URDF).getroot().findall("joint") if j.get("name", "").startswith("joint")]
    assert len(juntas) == len(g.JUNTAS) == 6
    for junta, (origen, eje) in zip(juntas, g.JUNTAS):
        assert tuple(map(float, junta.find("origin").get("xyz").split())) == pytest.approx(origen)
        assert tuple(map(float, junta.find("axis").get("xyz").split())) == pytest.approx(eje)
    assert np.degrees(float(juntas[2].find("limit").get("upper"))) == pytest.approx(g.LIMITES_ARTICULACIONES[2][1], abs=0.1)
    assert g.PUNTA_URDF_Z == pytest.approx(0.177)  # gripper_joint 0.02 + tcp 0.157
    assert g.LARGO_PINZA_DEFECTO == pytest.approx(g.PUNTA_URDF_Z + 0.040)  # más los 40 mm de los dedos largos


@pytest.mark.parametrize("pose", [DESCANSO, [0, 0, 90, 0, 90, 0], [0] * 6, [-30, 85, -80, -98, 90, -75]])
def test_las_poses_normales_son_validas(pose) -> None:
    assert g.problemas_de_pose(pose, Z_TOPE) == []


def test_el_codo_o_la_pinza_bajo_la_mesa_se_rechazan() -> None:
    problemas = g.problemas_de_pose([0, 120, 0, 0, 0, 0], Z_TOPE)
    assert any("atraviesa la mesa" in p and "codo" in p for p in problemas)
    assert any("pinza" in p for p in problemas)


def test_la_punta_no_puede_bajar_del_tablero() -> None:
    pose = [0, 100, 0, 0, 0, 0]
    assert any("por debajo del tablero" in p for p in g.problemas_de_pose(pose, Z_TOPE))
    assert g.punta_minima_para(Z_TOPE, 0.177) == pytest.approx(0.04365, abs=1e-4)  # 223,65 mm - 177 mm de pinza - 3 mm de tolerancia
    assert g.punta_minima_para(Z_TOPE) == pytest.approx(0.00365, abs=1e-4)  # con el largo por defecto (217 mm)
    assert g.punta_minima_para(None) == g.PUNTA_MINIMA_SIN_TABLERO


def test_un_angulo_fuera_del_rango_real_se_rechaza_con_su_articulacion() -> None:
    assert g.problemas_de_pose([0, 0, 170, 0, 0, 0]) == ["J3 (170°) está fuera de su rango real (-160° a 160°)"]
    assert "J2" in g.problemas_de_pose([0, 200, 0, 0, 0, 0])[0]
    assert g.problemas_de_pose([0, 0, 0]) == ["Hacen falta los 6 ángulos J1 a J6"]


def test_la_pinza_doblada_contra_el_antebrazo_es_un_choque() -> None:
    assert g.problemas_de_pose([332, 81, 13, -161, -244, 338], Z_TOPE) == ["el antebrazo y la pinza chocarían entre sí"]


def test_un_camino_con_extremos_validos_puede_ser_imposible() -> None:
    desde, hasta = [25, -10, 130, -145, 130, -245], [-95, 30, 40, -105, 105, -105]
    assert g.problemas_de_pose(desde, Z_TOPE) == [] and g.problemas_de_pose(hasta, Z_TOPE) == []
    problemas = g.problemas_de_trayectoria(desde, hasta, Z_TOPE)
    assert problemas and "chocarían" in problemas[0] and "del camino" in problemas[0]
    assert g.problemas_de_trayectoria(DESCANSO, [0, 0, 90, 0, 90, 0], Z_TOPE) == []


def test_una_pinza_mas_larga_baja_la_punta_y_cambia_lo_que_es_valido() -> None:
    pose = [0, 40, 0, 0, 0, 0]  # brazo inclinado hacia adelante con la pinza apuntando hacia arriba
    corta, larga = g.puntos_del_brazo(pose, 0.177), g.puntos_del_brazo(pose, 0.317)
    assert np.linalg.norm(larga["punta"] - corta["punta"]) == pytest.approx(0.14)  # la punta se corre los 14 cm de más, sobre el eje de la herramienta
    assert np.allclose(larga["articulaciones"][6], corta["articulaciones"][6])  # la brida no cambia, solo hasta dónde llegan los dedos
    assert g.problemas_de_pose([0, 0, 90, 0, 90, 0], Z_TOPE, 0.217) == []
    # el tablero queda `largo` por debajo de la brida: con una pinza más larga el piso exigido a la punta baja lo mismo
    assert g.punta_minima_para(Z_TOPE, 0.317) == pytest.approx(g.punta_minima_para(Z_TOPE, 0.217) - 0.1)
