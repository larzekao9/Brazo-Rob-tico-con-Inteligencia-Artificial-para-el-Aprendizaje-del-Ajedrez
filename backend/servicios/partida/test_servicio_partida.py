import pytest

from backend.servicios.partida import servicio_partida
from backend.servicios.partida.servicio_partida import (
    crear_partida,
    mover,
    mover_desde_foto,
    obtener_partida,
)


def test_crear_partida_arranca_en_posicion_inicial() -> None:
    partida = crear_partida(nivel=5)
    assert partida.fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")
    assert not partida.terminada
    assert partida.tipo_oponente == "motor"


def test_crear_partida_con_tipo_oponente_no_soportado_lanza_valueerror() -> None:
    # Se valida al crear, sin necesidad de Stockfish corriendo (HU10).
    with pytest.raises(ValueError):
        crear_partida(nivel=5, tipo_oponente="participante")


def test_crear_partida_con_fen_inicial_arranca_en_esa_posicion() -> None:
    # Posición tras 1. e4 e5 — simula lo que devolvería /vision/reconocer.
    fen_tablero_escaneado = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    partida = crear_partida(nivel=5, fen_inicial=fen_tablero_escaneado)
    assert partida.fen == fen_tablero_escaneado
    assert partida.jugadas_san == []  # todavía no se jugó nada *desde* que se cargó


def test_crear_partida_con_fen_inicial_invalido_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        crear_partida(nivel=5, fen_inicial="esto no es un fen")


def test_crear_partida_con_fen_inicial_imposible_lanza_valueerror() -> None:
    # 9 damas blancas — sintácticamente válido, pero imposible en una partida
    # real (visto en vivo con un FEN mal reconocido por visión, que hacía
    # caer a Stockfish más adelante en vez de fallar acá con un error claro).
    fen_imposible = "QQQQQQQQ/QPPPPPPP/8/8/8/8/8/K6k w - - 0 1"
    with pytest.raises(ValueError):
        crear_partida(nivel=5, fen_inicial=fen_imposible)


def test_obtener_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        obtener_partida("no-existe")


def test_mover_aplica_jugada_humana_y_responde_con_stockfish() -> None:
    partida = crear_partida(nivel=5)
    resultado = mover(partida.id, "e2e4")
    assert resultado["jugada_motor"] is not None
    assert not resultado["terminada"]
    # el FEN avanzó: ya no es la posición inicial
    assert "w KQkq - 0 1" not in resultado["fen"]


def test_mover_jugada_ilegal_lanza_valueerror() -> None:
    partida = crear_partida(nivel=5)
    with pytest.raises(ValueError):
        mover(partida.id, "e2e5")


def test_mover_en_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        mover("no-existe", "e2e4")


def test_mover_en_partida_ya_terminada_lanza_valueerror() -> None:
    # Fool's mate armado directo en el tablero, sin pasar por Stockfish, para dejar la
    # partida en jaque mate y probar que `mover` no deja seguir jugando después.
    partida = crear_partida(nivel=1)
    for jugada_san in ["f3", "e5", "g4", "Qh4#"]:
        partida.tablero.push_san(jugada_san)
    assert partida.terminada

    with pytest.raises(ValueError):
        mover(partida.id, "a2a3")


def test_mover_desde_foto_detecta_y_aplica_la_jugada(monkeypatch: pytest.MonkeyPatch) -> None:
    partida = crear_partida(nivel=5)
    # Simula que la cámara/reconocimiento ya vieron la posición tras 1. e4 —
    # detectar_jugada no usa el turno de fen_despues, así que el valor exacto no importa acá.
    fen_despues_e4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    monkeypatch.setattr(servicio_partida, "capturar_foto_tablero", lambda: None)
    monkeypatch.setattr(servicio_partida, "reconocer_tablero", lambda imagen, turno: fen_despues_e4)

    resultado = mover_desde_foto(partida.id)

    assert resultado["jugadas"][0] == "e4"
    assert resultado["jugada_motor"] is not None  # requiere Stockfish


def test_mover_desde_foto_sin_jugada_legal_que_coincida_lanza_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partida = crear_partida(nivel=5)
    # Posición imposible de alcanzar con una sola jugada legal desde la inicial.
    fen_irreconciliable = "8/8/8/8/8/8/8/8 b - - 0 1"
    monkeypatch.setattr(servicio_partida, "capturar_foto_tablero", lambda: None)
    monkeypatch.setattr(servicio_partida, "reconocer_tablero", lambda imagen, turno: fen_irreconciliable)

    with pytest.raises(ValueError):
        mover_desde_foto(partida.id)


def test_mover_desde_foto_en_partida_ya_terminada_lanza_valueerror() -> None:
    partida = crear_partida(nivel=1)
    for jugada_san in ["f3", "e5", "g4", "Qh4#"]:
        partida.tablero.push_san(jugada_san)
    assert partida.terminada

    with pytest.raises(ValueError):
        mover_desde_foto(partida.id)


def test_mover_desde_foto_en_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        mover_desde_foto("no-existe")
