"""Tests de los helpers de `ruta_aprendizaje` (la inferencia completa se prueba con el modelo en `test_inferencia.py`)."""
import chess

from backend.rutas.ruta_aprendizaje import _san_a_uci


def test_san_a_uci_convierte_una_jugada_legal() -> None:
    assert _san_a_uci(chess.Board(), "e4") == "e2e4"
    assert _san_a_uci(chess.Board(), "Nf3") == "g1f3"


def test_san_a_uci_respeta_de_quien_es_el_turno() -> None:
    tablero = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

    assert _san_a_uci(tablero, "e5") == "e7e5"


def test_san_a_uci_devuelve_vacio_si_la_jugada_no_es_valida() -> None:
    assert _san_a_uci(chess.Board(), "") == ""
    assert _san_a_uci(chess.Board(), "Qh5") == ""
