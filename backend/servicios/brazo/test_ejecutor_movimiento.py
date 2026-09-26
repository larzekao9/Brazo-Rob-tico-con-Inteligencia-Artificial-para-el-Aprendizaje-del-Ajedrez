from unittest.mock import MagicMock

import chess
import pytest

from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal

HOST_DOCUMENTACION = "192.0.2.1"


def test_ejecutor_real_enviar_comando_con_socket_mockeado():
    ejecutor = EjecutorReal(host=HOST_DOCUMENTACION)
    socket_mock = MagicMock()
    socket_mock.recv.return_value = b"0,{},EnableRobot();"
    ejecutor._socket = socket_mock

    respuesta = ejecutor._enviar_comando("EnableRobot()")

    socket_mock.sendall.assert_called_once_with(b"EnableRobot()")
    assert respuesta == "0,{},EnableRobot();"


def test_ejecutor_real_ejecutar_movimiento_lanza_not_implemented_error():
    ejecutor = EjecutorReal(host=HOST_DOCUMENTACION)

    with pytest.raises(NotImplementedError):
        ejecutor.ejecutar_movimiento("e2", "e4", captura=False)


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
