from unittest.mock import MagicMock

import chess
import pytest

from backend.servicios.brazo.calibracion_tablero import (
    PuntoCalibracion,
    calcular_posiciones_casillas,
)
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal

HOST_DOCUMENTACION = "192.0.2.1"

PUNTOS_CALIBRACION_SINTETICOS = [
    PuntoCalibracion(casilla="a1", x=0.0, y=0.0, z=10.0),
    PuntoCalibracion(casilla="h1", x=700.0, y=0.0, z=10.0),
    PuntoCalibracion(casilla="a8", x=0.0, y=700.0, z=10.0),
]


def test_ejecutor_real_enviar_comando_con_socket_mockeado():
    ejecutor = EjecutorReal(host=HOST_DOCUMENTACION)
    socket_mock = MagicMock()
    socket_mock.recv.return_value = b"0,{},EnableRobot();"
    ejecutor._socket = socket_mock

    respuesta = ejecutor._enviar_comando("EnableRobot()")

    socket_mock.sendall.assert_called_once_with(b"EnableRobot()")
    assert respuesta == "0,{},EnableRobot();"


def test_ejecutor_real_ejecutar_movimiento_sin_calibracion_lanza_runtime_error():
    ejecutor = EjecutorReal(host=HOST_DOCUMENTACION)

    with pytest.raises(RuntimeError):
        ejecutor.ejecutar_movimiento("e2", "e4", captura=False)


def test_ejecutor_real_ejecutar_movimiento_con_captura_lanza_not_implemented_error():
    posiciones = calcular_posiciones_casillas(PUNTOS_CALIBRACION_SINTETICOS)
    ejecutor = EjecutorReal(host=HOST_DOCUMENTACION, posiciones_casillas=posiciones)

    with pytest.raises(NotImplementedError):
        ejecutor.ejecutar_movimiento("e2", "e4", captura=True)


def test_ejecutor_real_ejecutar_movimiento_envia_secuencia_de_comandos_sin_captura():
    posiciones = calcular_posiciones_casillas(PUNTOS_CALIBRACION_SINTETICOS)
    ejecutor = EjecutorReal(
        host=HOST_DOCUMENTACION,
        posiciones_casillas=posiciones,
        altura_segura_mm=50.0,
        pin_efector_do=1,
    )
    socket_mock = MagicMock()
    socket_mock.recv.return_value = b"0,{},MovJ();"
    ejecutor._socket = socket_mock

    ejecutor.ejecutar_movimiento("e2", "e4", captura=False)

    comandos = [llamada.args[0].decode("ascii") for llamada in socket_mock.sendall.call_args_list]
    assert len(comandos) == 8
    assert comandos[0].startswith("MovJ(")
    assert comandos[1].startswith("MovL(")
    assert comandos[2] == "DO(1,1)"
    assert comandos[3].startswith("MovL(")
    assert comandos[4].startswith("MovJ(")
    assert comandos[5].startswith("MovL(")
    assert comandos[6] == "DO(1,0)"
    assert comandos[7].startswith("MovL(")


pytest.importorskip("pybullet")
from backend.servicios.brazo.ejecutor_movimiento import EjecutorSimulado


def test_ejecutor_simulado_ejecuta_movimiento_legal_y_actualiza_tablero():
    ejecutor = EjecutorSimulado(modo_gui=False)
    try:
        ejecutor.ejecutar_movimiento("e2", "e4", captura=False)

        pieza_en_e4 = ejecutor.tablero.piece_at(chess.parse_square("e4"))
        assert pieza_en_e4 is not None
        assert pieza_en_e4.piece_type == chess.PAWN
        assert ejecutor.tablero.piece_at(chess.parse_square("e2")) is None
        assert len(ejecutor.piezas) == 32
    finally:
        ejecutor.cerrar()
