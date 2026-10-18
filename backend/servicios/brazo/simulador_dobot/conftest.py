"""Fixtures de los tests del simulador: se omiten si PyBullet no está instalado (salvo los que no lo usan)."""
from __future__ import annotations

import dataclasses

import pytest

from backend.servicios.brazo.simulador_dobot import calibracion_ejemplo as ejemplo
from backend.servicios.brazo.simulador_dobot.nucleo import Simulador
from backend.servicios.brazo.simulador_dobot.protocolo import ProtocoloDobot
from backend.servicios.brazo.simulador_dobot.servidor_tcp import ServidorDashboard

FEN_UN_PEON = "8/8/8/8/8/8/4P3/8 w - - 0 1"
FEN_UN_CABALLO = "8/8/8/8/8/8/8/1N6 w - - 0 1"


def pose_agarre(simulador: Simulador, casilla: str, sobre_mm: float = 0.0, desplazamiento: tuple[float, float] = (0.0, 0.0)):
    """Pose de la brida con las puntas 3 mm sobre el tablero (más `sobre_mm`) en `casilla`, con los dedos en diagonal."""
    x, y, _ = simulador.calibracion.posiciones_casillas[casilla]
    z = simulador.z_tope + 3.0 + sobre_mm
    return (x + desplazamiento[0], y + desplazamiento[1], z, -180.0, 0.0, simulador.rz_referencia + 45.0)


def mover_y_esperar(simulador: Simulador, pose, articular: bool = False, velocidad_pct: float = 100.0) -> None:
    """Encola un movimiento y avanza la simulación a mano hasta que termina."""
    simulador.encolar_pose(pose, articular, velocidad_pct, 100.0, None)
    for _ in range(4000):
        if simulador.actual is None and not simulador.cola:
            return
        simulador.avanzar(0.05)
    raise AssertionError("el movimiento no terminó")


@pytest.fixture
def parametros_agarre():
    return dataclasses.replace(ejemplo.parametros_agarre_ejemplo(), velocidad_pinza=100)


@pytest.fixture
def crear_simulador(parametros_agarre):
    """Fábrica de simuladores sin hilo (se avanzan a mano); los cierra todos al terminar."""
    creados: list[Simulador] = []

    def fabrica(fen: str = FEN_UN_PEON, con_fisica: bool = True, **extra) -> Simulador:
        if con_fisica:
            pytest.importorskip("pybullet")
        simulador = Simulador(ejemplo.calibracion_ejemplo(), parametros_agarre, fen, con_fisica, tiempo_real=False, **extra)
        creados.append(simulador)
        return simulador

    yield fabrica
    for simulador in creados:
        simulador.cerrar()


@pytest.fixture
def servicio(parametros_agarre):
    """Simulador con hilo (20 veces más rápido que el tiempo real) y servidor TCP en un puerto libre."""
    pytest.importorskip("pybullet")
    simulador = Simulador(ejemplo.calibracion_ejemplo(), parametros_agarre, FEN_UN_PEON, True, escala_tiempo=20.0)
    protocolo = ProtocoloDobot(simulador)
    servidor = ServidorDashboard(protocolo, "127.0.0.1", 0)
    servidor.iniciar()
    simulador.iniciar_hilo()
    yield simulador, protocolo, servidor
    servidor.detener()
    simulador.cerrar()
