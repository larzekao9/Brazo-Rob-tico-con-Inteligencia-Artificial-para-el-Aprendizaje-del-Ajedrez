"""Interpolación en el tiempo: el TCP no salta, respeta `SpeedFactor` y las articulaciones son coherentes con la pose."""
import math

import pytest

from backend.servicios.brazo.simulador_dobot import cinematica
from backend.servicios.brazo.simulador_dobot.conftest import pose_agarre
from backend.servicios.brazo.simulador_dobot.nucleo import ErrorDeComando


def _duracion_de_movimiento_lineal(simulador, velocidad_global: int) -> float:
    simulador.velocidad_global = velocidad_global
    inicio = simulador.pose
    destino = (inicio[0] + 100.0, inicio[1], inicio[2], inicio[3], inicio[4], inicio[5])
    simulador.encolar_pose(destino, False, 20.0, 100.0, None)
    transcurrido = 0.0
    while simulador.actual is not None or simulador.cola:
        simulador.avanzar(0.02)
        transcurrido += 0.02
    assert simulador.pose[0] == pytest.approx(destino[0], abs=1e-6)
    return transcurrido


def test_movimiento_lineal_no_es_instantaneo_y_avanza_de_a_poco(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    simulador.velocidad_global = 20
    inicio = simulador.pose
    simulador.encolar_pose((inicio[0] + 40.0, inicio[1], inicio[2], *inicio[3:]), False, 20.0, 10.0, None)
    simulador.avanzar(0.05)
    assert simulador.actual is not None
    assert inicio[0] < simulador.pose[0] < inicio[0] + 40.0
    anteriores = [simulador.pose[0]]
    for _ in range(10):
        simulador.avanzar(0.1)
        anteriores.append(simulador.pose[0])
    assert all(b >= a for a, b in zip(anteriores, anteriores[1:]))
    assert simulador.pose[1] == pytest.approx(inicio[1], abs=1e-6)


def test_speedfactor_a_la_mitad_duplica_la_duracion(crear_simulador):
    rapido = _duracion_de_movimiento_lineal(crear_simulador(con_fisica=False), 40)
    lento = _duracion_de_movimiento_lineal(crear_simulador(con_fisica=False), 20)
    assert lento == pytest.approx(2 * rapido, rel=0.08)


def test_velocidad_absoluta_speed_manda_sobre_el_speedfactor(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    simulador.velocidad_global = 100
    inicio = simulador.pose
    simulador.encolar_pose((inicio[0] + 50.0, *inicio[1:]), False, 100.0, 100.0, 50.0)
    transcurrido = 0.0
    while simulador.actual is not None or simulador.cola:
        simulador.avanzar(0.05)
        transcurrido += 0.05
    assert 1.0 <= transcurrido <= 1.5


def test_cola_ejecuta_en_orden_y_stop_la_vacia(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    inicio = simulador.pose
    primero = simulador.encolar_pose((inicio[0] + 30.0, *inicio[1:]), False, 50.0, 50.0, None)
    segundo = simulador.encolar_pose((inicio[0] + 30.0, inicio[1] + 30.0, *inicio[2:]), False, 50.0, 50.0, None)
    assert segundo == primero + 1
    simulador.avanzar(0.1)
    assert simulador.modo() == 7
    simulador.detener()
    assert simulador.modo() == 5
    parada = simulador.pose
    simulador.avanzar(0.5)
    assert simulador.pose == parada


def test_pose_fuera_de_alcance_y_bajo_el_tablero_dan_error_del_dobot(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    with pytest.raises(ErrorDeComando) as fuera:
        simulador.encolar_pose((50.0, 50.0, 300.0, -180.0, 0.0, 0.0), False, 20.0, 10.0, None)
    assert fuera.value.codigo == -1
    with pytest.raises(ErrorDeComando) as bajo:
        simulador.encolar_pose((300.0, 0.0, simulador.z_tope - 2.0, -180.0, 0.0, 0.0), False, 20.0, 10.0, None)
    assert bajo.value.codigo == -1
    simulador.encolar_pose((300.0, 0.0, simulador.z_tope + 3.0, -180.0, 0.0, 0.0), False, 20.0, 10.0, None)


def test_movimiento_articular_llega_a_los_angulos_y_a_la_pose_equivalente(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    destino = cinematica.angulos_para_pose(350.0, 100.0, 400.0, -75.0)
    simulador.encolar_angulos(destino, 100.0, 100.0)
    while simulador.actual is not None or simulador.cola:
        simulador.avanzar(0.05)
    assert simulador.angulos == pytest.approx(destino, abs=1e-6)
    assert simulador.pose[:3] == pytest.approx((350.0, 100.0, 400.0), abs=1e-6)


def test_rotacion_de_la_muneca_toma_el_camino_corto(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    x, y, z = simulador.pose[:3]
    simulador.encolar_pose((x, y, z, -180.0, 0.0, 170.0), False, 100.0, 100.0, None)
    giros = []
    while simulador.actual is not None or simulador.cola:
        simulador.avanzar(0.02)
        giros.append(simulador.pose[5])
    assert all(giro <= -118.0 or giro >= 168.0 for giro in giros)


def test_cinematica_ida_y_vuelta_y_alcance():
    angulos = cinematica.angulos_para_pose(400.0, -120.0, 350.0, -75.0)
    pose = cinematica.pose_para_angulos(angulos)
    assert pose[:3] == pytest.approx((400.0, -120.0, 350.0), abs=1e-6)
    assert pose[5] == pytest.approx(-75.0, abs=1e-6)
    assert cinematica.angulos_para_pose(1500.0, 0.0, 300.0, 0.0) is None
    assert cinematica.angulos_para_pose(10.0, 10.0, 300.0, 0.0) is None
    puntos = cinematica.puntos_del_brazo(angulos)
    assert len(puntos) == 5 and math.dist(puntos[0], puntos[1]) == pytest.approx(cinematica.ALTURA_HOMBRO_MM)


def test_pose_inicial_es_la_posicion_cero_de_la_calibracion(crear_simulador):
    simulador = crear_simulador(con_fisica=False)
    assert simulador.pose[:3] == pytest.approx(cinematica.pose_para_angulos(simulador.calibracion.angulos_cero)[:3], abs=1e-6)
    destino = pose_agarre(simulador, "e4", sobre_mm=80)
    simulador.encolar_pose(destino, True, 100.0, 100.0, None)
    while simulador.actual is not None or simulador.cola:
        simulador.avanzar(0.05)
    assert simulador.pose[:3] == pytest.approx(destino[:3], abs=1e-6)
