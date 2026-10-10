from collections.abc import Callable

import chess
import pytest

from backend.servicios.aprendizaje.analisis_red import analizar_partida_con_red

FEN_INICIAL = chess.STARTING_FEN


def _fen_despues_de(*jugadas_san: str) -> str:
    tablero = chess.Board()
    for san in jugadas_san:
        tablero.push_san(san)
    return tablero.fen()


def _predictor_guionado() -> Callable[[str, int], list[tuple[str, float]]]:
    """Predictor falso: en la posición inicial elige d4 (distinto de e4); tras 1.e4 elige e5."""
    candidatas = {
        FEN_INICIAL: [("d4", 0.5), ("e4", 0.3), ("c4", 0.2)],
        _fen_despues_de("e4"): [("e5", 0.6), ("c5", 0.4)],
    }
    return lambda fen, top_n: candidatas[fen][:top_n]


def test_registra_coincidencia_y_lados_de_cada_jugada() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, ["e4", "e5"], tipo_oponente="modelo", predictor=_predictor_guionado()
    )
    primera, segunda = resultado["jugadas"]

    assert primera["numero"] == 1 and primera["color"] == "blancas" and primera["quien"] == "jugador"
    assert primera["red_elige"] == "d4"
    assert primera["coincide"] is False
    assert primera["probabilidad_jugada"] == 0.3  # e4 sí estaba entre las candidatas
    assert segunda["color"] == "negras" and segunda["quien"] == "modelo"
    assert segunda["red_elige"] == "e5" and segunda["coincide"] is True


def test_resumen_separa_jugador_y_contraparte() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, ["e4", "e5"], tipo_oponente="modelo", predictor=_predictor_guionado()
    )
    resumen = resultado["resumen"]

    assert resumen["total_jugadas"] == 2
    assert resumen["coinciden"] == 1
    assert resumen["porcentaje"] == 50.0
    assert resumen["jugador"] == {"total": 1, "coinciden": 0, "porcentaje": 0.0}
    assert resumen["contraparte"] == {"total": 1, "coinciden": 1, "porcentaje": 100.0}


def test_contraparte_motor_se_etiqueta_como_motor() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, ["e4", "e5"], tipo_oponente="motor", predictor=_predictor_guionado()
    )
    assert resultado["jugadas"][1]["quien"] == "motor"


def test_jugada_fuera_de_las_candidatas_no_tiene_probabilidad() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, ["g3"], tipo_oponente="motor", predictor=lambda fen, n: [("d4", 0.9)]
    )
    jugada = resultado["jugadas"][0]
    assert jugada["probabilidad_jugada"] is None
    assert jugada["coincide"] is False


def test_sin_candidatas_la_red_no_elige_nada() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, ["e4"], tipo_oponente="motor", predictor=lambda fen, n: []
    )
    jugada = resultado["jugadas"][0]
    assert jugada["red_elige"] is None
    assert jugada["probabilidad_red"] is None
    assert jugada["coincide"] is False


def test_partida_sin_jugadas_da_resumen_vacio() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, [], tipo_oponente="motor", predictor=_predictor_guionado()
    )
    assert resultado["jugadas"] == []
    assert resultado["resumen"]["total_jugadas"] == 0
    assert resultado["resumen"]["porcentaje"] is None


def test_jugada_ilegal_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        analizar_partida_con_red(
            FEN_INICIAL, ["e5"], tipo_oponente="motor", predictor=_predictor_guionado()
        )


def test_cada_jugada_incluye_la_jugada_real_en_uci() -> None:
    resultado = analizar_partida_con_red(
        FEN_INICIAL, ["e4", "e5"], tipo_oponente="modelo", predictor=_predictor_guionado()
    )

    assert [j["jugada_uci"] for j in resultado["jugadas"]] == ["e2e4", "e7e5"]
