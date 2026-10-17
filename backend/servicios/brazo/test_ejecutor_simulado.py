"""Ejecutor simulado (PyBullet): se omite entero si pybullet no está instalado."""
import chess
import pytest

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
