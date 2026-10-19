"""Pruebas unitarias para el emulador virtual del Dobot CR5AS y pinza PGE-50-26."""
import time
import pytest
import chess

from backend.servicios.brazo.emulador_dobot import EmuladorDobot
from backend.servicios.brazo.cliente_dobot import ClienteDobot
from backend.servicios.brazo.pinza_dh import PinzaDH, REG_POSICION, REG_ESTADO_AGARRE, AGARRE_SOSTIENE
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal
from backend.servicios.brazo.calibracion_brazo import ParametrosAgarre


@pytest.fixture
def emulador_dobot():
    """Inicia el emulador en un puerto de prueba y lo detiene al finalizar."""
    emulador = EmuladorDobot(host="127.0.0.1", puerto=29995)
    emulador.iniciar()
    time.sleep(0.05)
    yield emulador
    emulador.detener()


def test_conexion_cliente_dobot_con_emulador(emulador_dobot):
    cliente = ClienteDobot(host="127.0.0.1", puerto=29995, timeout_segundos=1.0)
    cliente.conectar()
    try:
        assert cliente.modo() == 5
        pose = cliente.pose()
        assert len(pose) == 6
        angulos = cliente.angulos()
        assert len(angulos) == 6
    finally:
        cliente.cerrar()


def test_control_pinza_con_emulador(emulador_dobot):
    cliente = ClienteDobot(host="127.0.0.1", puerto=29995, timeout_segundos=1.0)
    cliente.conectar()
    pinza = PinzaDH(cliente)
    pinza.conectar()
    try:
        estado_ini = pinza.estado()
        assert estado_ini.inicializada is True
        
        # Mover pinza a posición 560
        pinza.mover_a(560)
        estado_despues = pinza.estado()
        assert estado_despues.posicion == 560
    finally:
        pinza.desconectar()
        cliente.cerrar()


def test_ejecutor_real_movimiento_completo_con_emulador(emulador_dobot):
    # Coordenadas simuladas
    posiciones = {
        "e2": (0.0, -560.0, 235.0),
        "e4": (0.0, -498.0, 235.0),
    }
    orientacion = (-180.0, 0.0, -120.0)
    angulos_cero = (302.85, 28.21, -149.12, 30.90, 89.71, -27.81)

    cliente = ClienteDobot(host="127.0.0.1", puerto=29995, timeout_segundos=1.0)
    pinza = PinzaDH(cliente)

    ejecutor = EjecutorReal(
        host="127.0.0.1",
        puerto_dashboard=29995,
        posiciones_casillas=posiciones,
        orientacion=orientacion,
        angulos_cero=angulos_cero,
        parametros=ParametrosAgarre(z_tope=223.65, margen_agarre_mm=3.0, altura_segura_mm=80.0),
        cliente=cliente,
        pinza=pinza,
    )
    ejecutor.conectar()
    try:
        tablero = chess.Board()
        jugada = chess.Move.from_uci("e2e4")
        ejecutor.ejecutar_movimiento(tablero, jugada)
        assert len(emulador_dobot.estado.historial_movimientos) > 0
    finally:
        ejecutor.desconectar()
