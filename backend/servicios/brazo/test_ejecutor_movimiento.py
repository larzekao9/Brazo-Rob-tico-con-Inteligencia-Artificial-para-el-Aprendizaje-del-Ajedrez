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
    tablero_antes = chess.Board()
    jugada = tablero_antes.parse_uci("e2e4")

    with pytest.raises(RuntimeError):
        ejecutor.ejecutar_movimiento(tablero_antes, jugada)


def test_ejecutor_real_ejecutar_movimiento_con_captura_lanza_not_implemented_error():
    posiciones = calcular_posiciones_casillas(PUNTOS_CALIBRACION_SINTETICOS)
    ejecutor = EjecutorReal(host=HOST_DOCUMENTACION, posiciones_casillas=posiciones)
    tablero_antes = chess.Board()
    tablero_antes.push_san("e4")
    tablero_antes.push_san("d5")
    jugada = tablero_antes.parse_uci("e4d5")

    with pytest.raises(NotImplementedError):
        ejecutor.ejecutar_movimiento(tablero_antes, jugada)


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
    tablero_antes = chess.Board()
    jugada = tablero_antes.parse_uci("e2e4")

    ejecutor.ejecutar_movimiento(tablero_antes, jugada)

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
        tablero_antes = chess.Board()
        jugada = tablero_antes.parse_uci("e2e4")

        ejecutor.ejecutar_movimiento(tablero_antes, jugada)

        assert "e4" in ejecutor.piezas
        assert "e2" not in ejecutor.piezas
        assert len(ejecutor.piezas) == 32
        # el tablero que pasó el llamador no se muta ni queda referenciado
        # como estado interno del ejecutor (fix de sincronización).
        assert tablero_antes.fen() == chess.STARTING_FEN
    finally:
        ejecutor.cerrar()


def test_ejecutor_simulado_dos_jugadas_de_estrategia_no_consecutivas_no_se_desincroniza():
    # Reproduce el escenario real: el ejecutor solo recibe la jugada de la
    # estrategia (nunca la del humano) — dos llamadas sucesivas representan
    # la 2da y 4ta jugada real de la partida, con jugadas del humano en el
    # medio que el ejecutor nunca vio. Con un tablero interno acumulado
    # (el bug original) esto se desincronizaba; con `tablero_antes` pasado
    # en cada llamada, cada una es independiente y correcta.
    ejecutor = EjecutorSimulado(modo_gui=False)
    try:
        tablero_1 = chess.Board()
        tablero_1.push_san("e4")
        tablero_1.push_san("e5")
        jugada_1 = tablero_1.parse_uci("g1f3")
        ejecutor.ejecutar_movimiento(tablero_1, jugada_1)

        tablero_2 = tablero_1.copy()
        tablero_2.push(jugada_1)
        tablero_2.push_san("Nc6")
        jugada_2 = tablero_2.parse_uci("f1c4")
        ejecutor.ejecutar_movimiento(tablero_2, jugada_2)

        assert "c4" in ejecutor.piezas
        assert "f1" not in ejecutor.piezas
        assert "f3" in ejecutor.piezas
    finally:
        ejecutor.cerrar()
