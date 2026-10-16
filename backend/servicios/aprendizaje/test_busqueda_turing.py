"""Búsqueda de Turing: evaluación, tácticas y combinación con las probabilidades de la red (sin cargar ninguna red)."""
import math

import chess
import pytest

from backend.servicios.aprendizaje.busqueda_turing import MATE, buscar, evaluar, explicar_decision


def _jugada(tablero: chess.Board, san: str) -> chess.Move:
    return tablero.parse_san(san)


# --- evaluación -------------------------------------------------------------------------------------------------------
def test_la_posicion_inicial_esta_igualada() -> None:
    assert evaluar(chess.Board()) == 0


def test_la_evaluacion_es_simetrica_al_espejar_la_posicion() -> None:
    tablero = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")

    assert evaluar(tablero) == evaluar(tablero.mirror())


def test_una_dama_de_mas_vale_unos_900_centipeones() -> None:
    sin_dama_negra = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    assert 800 < evaluar(sin_dama_negra) < 1000


def test_la_evaluacion_es_desde_quien_tiene_el_turno() -> None:
    blancas = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    negras = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1")

    assert evaluar(blancas) > 0 > evaluar(negras)


# --- tácticas ---------------------------------------------------------------------------------------------------------
def test_encuentra_el_mate_en_uno() -> None:
    tablero = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")

    resultado = buscar(tablero, profundidad=2)

    assert tablero.san(resultado.jugada) == "Qxf7#" and resultado.puntaje > MATE - 1000


def test_encuentra_el_mate_del_pasillo() -> None:
    tablero = chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")

    assert tablero.san(buscar(tablero, profundidad=2).jugada) == "Ra8#"


def test_captura_la_dama_que_quedo_colgada() -> None:
    tablero = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/4P2q/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1")

    assert tablero.san(buscar(tablero, profundidad=3).jugada) == "Nxh4"


def test_no_regala_la_dama_aunque_la_red_la_prefiera() -> None:
    # La red (probabilidades inventadas) quiere Qd4??, que pierde la dama por exd4; el cálculo lo corrige.
    tablero = chess.Board("4k3/8/8/4p3/8/8/3Q4/4K3 w - - 0 1")
    probabilidades = {j: 0.02 for j in tablero.legal_moves}
    probabilidades[_jugada(tablero, "Qd4")] = 0.7

    resultado = buscar(tablero, probabilidades, profundidad=3)

    assert tablero.san(resultado.jugada) != "Qd4"


def test_con_mucho_peso_la_red_decide_si_el_calculo_no_ve_diferencia() -> None:
    tablero = chess.Board()
    probabilidades = {j: 0.001 for j in tablero.legal_moves}
    probabilidades[_jugada(tablero, "e4")] = 0.5

    assert tablero.san(buscar(tablero, probabilidades, profundidad=2, peso_red=200).jugada) == "e4"


def test_con_peso_cero_manda_solo_el_calculo() -> None:
    tablero = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/4P2q/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1")
    probabilidades = {j: 0.001 for j in tablero.legal_moves}
    probabilidades[_jugada(tablero, "a3")] = 0.9  # la red prefiere una jugada tonta

    assert tablero.san(buscar(tablero, probabilidades, profundidad=3, peso_red=0).jugada) == "Nxh4"


# --- robustez ---------------------------------------------------------------------------------------------------------
def test_siempre_devuelve_una_jugada_legal() -> None:
    for fen in (chess.STARTING_FEN, "r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9"):
        tablero = chess.Board(fen)

        assert buscar(tablero, profundidad=2).jugada in tablero.legal_moves


def test_con_una_sola_jugada_legal_la_devuelve_sin_calcular() -> None:
    tablero = chess.Board("7k/8/8/8/8/8/6q1/7K w - - 0 1")  # solo Kxg2
    resultado = buscar(tablero)

    assert tablero.san(resultado.jugada) == "Kxg2" and len(list(tablero.legal_moves)) == 1


def test_sin_jugadas_legales_da_error() -> None:
    with pytest.raises(ValueError):
        buscar(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"))  # ahogado


def test_con_tiempo_casi_nulo_igual_responde() -> None:
    tablero = chess.Board("r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9")

    resultado = buscar(tablero, profundidad=6, tiempo_limite=0.001)

    assert resultado.jugada in tablero.legal_moves


def test_la_busqueda_no_modifica_el_tablero_recibido() -> None:
    tablero = chess.Board("r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9")
    antes = tablero.fen()

    buscar(tablero, profundidad=3)

    assert tablero.fen() == antes and not tablero.move_stack


def test_profundidad_mayor_nunca_calcula_menos() -> None:
    tablero = chess.Board("r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9")

    assert buscar(tablero, profundidad=3, tiempo_limite=None).nodos > buscar(tablero, profundidad=1, tiempo_limite=None).nodos


# --- desglose de la decisión (panel de Razonamiento Neuronal) ---------------------------------------------------------
def test_explicar_decision_corrige_a_la_red_cuando_regala_la_dama() -> None:
    tablero = chess.Board("4k3/8/8/4p3/8/8/3Q4/4K3 w - - 0 1")
    probabilidades = {j: 0.02 for j in tablero.legal_moves}
    probabilidades[_jugada(tablero, "Qd4")] = 0.7

    desglose = explicar_decision(tablero, probabilidades, profundidad=3, tiempo_limite=None, maximo_candidatas=30)

    assert desglose["jugada_red_sola"] == "Qd4" and desglose["jugada"] != "Qd4" and desglose["corrige_a_la_red"]
    por_jugada = {c["jugada"]: c for c in desglose["candidatas"]}
    assert por_jugada["Qd4"]["calculo_cp"] < por_jugada[desglose["jugada"]]["calculo_cp"]  # regalar la dama se paga en el cálculo


def test_explicar_decision_el_puntaje_es_el_calculo_mas_el_aporte_de_la_red() -> None:
    tablero = chess.Board("r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9")
    probabilidades = {j: 1 / len(list(tablero.legal_moves)) for j in tablero.legal_moves}

    desglose = explicar_decision(tablero, probabilidades, profundidad=2, tiempo_limite=None, peso_red=40.0)

    for c in desglose["candidatas"]:
        assert abs(c["puntaje"] - (c["calculo_cp"] + 40.0 * math.log(c["probabilidad"]))) <= 1


def test_explicar_decision_marca_una_sola_elegida_y_es_la_de_mayor_puntaje() -> None:
    tablero = chess.Board("r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9")
    probabilidades = {j: 0.05 for j in tablero.legal_moves}

    desglose = explicar_decision(tablero, probabilidades, profundidad=2, tiempo_limite=None)

    elegidas = [c for c in desglose["candidatas"] if c["elegida"]]
    puntajes = [c["puntaje"] for c in desglose["candidatas"]]
    assert len(elegidas) == 1 and elegidas[0]["jugada"] == desglose["jugada"] and puntajes == sorted(puntajes, reverse=True)
    assert len(desglose["candidatas"]) <= 6 and desglose["nodos"] > 0 and desglose["tiempo_ms"] >= 0


def test_explicar_decision_detecta_el_mate_en_uno() -> None:
    tablero = chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    probabilidades = {j: 0.05 for j in tablero.legal_moves}

    desglose = explicar_decision(tablero, probabilidades, profundidad=2, tiempo_limite=None)

    assert desglose["jugada"] == "Ra8#" and desglose["candidatas"][0]["mate"]


def test_explicar_decision_si_la_red_acierta_no_hay_correccion() -> None:
    tablero = chess.Board()
    probabilidades = {j: 0.001 for j in tablero.legal_moves}
    probabilidades[_jugada(tablero, "e4")] = 0.6

    desglose = explicar_decision(tablero, probabilidades, profundidad=2, tiempo_limite=None, peso_red=200)

    assert desglose["jugada"] == "e4" and not desglose["corrige_a_la_red"]
