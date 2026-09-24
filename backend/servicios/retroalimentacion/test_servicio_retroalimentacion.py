import pytest
import chess

from backend.servicios.retroalimentacion.servicio_retroalimentacion import (
    analizar_jugada_en_tiempo_real,
    centipawns_a_probabilidad_victoria,
    clasificar_calidad_jugada,
    explicar_jugada,
    generar_resumen_partida,
)


def test_centipawns_a_probabilidad_victoria_posicion_igualada():
    prob = centipawns_a_probabilidad_victoria(0)
    assert prob == 50.0


def test_centipawns_a_probabilidad_victoria_con_ventaja_blanca():
    prob = centipawns_a_probabilidad_victoria(300)
    assert prob > 70.0 and prob < 85.0


def test_centipawns_a_probabilidad_victoria_con_desventaja():
    prob = centipawns_a_probabilidad_victoria(-300)
    assert prob > 15.0 and prob < 30.0


def test_centipawns_a_probabilidad_victoria_mate():
    assert centipawns_a_probabilidad_victoria(None, mate_en=2) == 100.0
    assert centipawns_a_probabilidad_victoria(None, mate_en=-1) == 0.0


def test_clasificar_calidad_jugada():
    assert clasificar_calidad_jugada(0, es_mejor_jugada=True) == "mejor"
    assert clasificar_calidad_jugada(20, es_mejor_jugada=False) == "excelente"
    assert clasificar_calidad_jugada(45, es_mejor_jugada=False) == "buena"
    assert clasificar_calidad_jugada(80, es_mejor_jugada=False) == "imprecision"
    assert clasificar_calidad_jugada(150, es_mejor_jugada=False) == "error"
    assert clasificar_calidad_jugada(350, es_mejor_jugada=False) == "blunder"
    assert clasificar_calidad_jugada(0, es_mejor_jugada=False, mate_en_despues=-2) == "blunder"


def test_explicar_jugada_control_centro():
    fen_antes = chess.STARTING_FEN
    fen_despues = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    principio, exp = explicar_jugada(
        fen_antes=fen_antes,
        jugada_san="e4",
        fen_despues=fen_despues,
        mejor_jugada_san="e4",
        clasificacion="mejor",
        perdida_cp=0,
    )
    assert principio == "control_del_centro"
    assert "central" in exp.lower()


def test_explicar_jugada_desarrollo_caballo():
    fen_antes = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    fen_despues = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    principio, exp = explicar_jugada(
        fen_antes=fen_antes,
        jugada_san="Nf3",
        fen_despues=fen_despues,
        mejor_jugada_san="Nf3",
        clasificacion="mejor",
        perdida_cp=0,
    )
    assert principio == "desarrollo_piezas"
    assert "caballo" in exp.lower()


def test_explicar_jugada_enroque():
    fen_antes = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5"
    tablero = chess.Board(fen_antes)
    mov = tablero.parse_san("O-O")
    tablero.push(mov)
    fen_despues = tablero.fen()

    principio, exp = explicar_jugada(
        fen_antes=fen_antes,
        jugada_san="O-O",
        fen_despues=fen_despues,
        mejor_jugada_san="O-O",
        clasificacion="mejor",
        perdida_cp=0,
    )
    assert principio == "seguridad_del_rey"
    assert "enroque" in exp.lower()


def test_analizar_jugada_en_tiempo_real():
    fen_antes = chess.STARTING_FEN
    fen_despues = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    resultado = analizar_jugada_en_tiempo_real(
        fen_antes=fen_antes,
        jugada_san="e4",
        fen_despues=fen_despues,
        evaluacion_antes_cp=20,
        evaluacion_despues_cp=25,
        mejor_jugada_san="e4",
    )
    assert resultado["calidad"] == "mejor"
    assert resultado["perdida_cp"] == 0
    assert resultado["probabilidad_victoria"] > 50.0
    assert "explicacion" in resultado
    assert "principio_ajedrecistico" in resultado


def test_generar_resumen_partida():
    analisis_mock = [
        {"numero_ply": 1, "calidad": "mejor", "probabilidad_victoria": 53.0, "jugada_san": "e4"},
        {"numero_ply": 2, "calidad": "buena", "probabilidad_victoria": 51.0, "jugada_san": "e5"},
        {"numero_ply": 3, "calidad": "imprecision", "probabilidad_victoria": 45.0, "jugada_san": "a3"},
    ]
    resumen = generar_resumen_partida(analisis_mock)
    assert resumen["precision_global"] > 60.0
    assert resumen["conteo_calidad"]["mejor"] == 1
    assert resumen["conteo_calidad"]["buena"] == 1
    assert resumen["conteo_calidad"]["imprecision"] == 1
    assert len(resumen["curva_efectividad"]) == 3
    assert len(resumen["consejo_tutor"]) > 10
