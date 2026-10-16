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


# --- /aprendizaje/inferencia con el desglose del cálculo (red y Stockfish de mentira) ---------------------------------
def _cliente_con_red_de_mentira(monkeypatch, red_prefiere: str):
    """Cliente HTTP donde la red prefiere `red_prefiere` (SAN) en la posición dada y Stockfish siempre dice 0."""
    from fastapi.testclient import TestClient

    from backend.main import app
    from backend.rutas import ruta_aprendizaje as ruta

    def probabilidades(tablero, *args, **kwargs):
        reparto = {j: 0.02 for j in tablero.legal_moves}
        reparto[tablero.parse_san(red_prefiere)] = 0.7
        return reparto

    monkeypatch.setattr(ruta, "predecir_top_jugadas", lambda fen, top_n=3: [(red_prefiere, 0.7)])
    monkeypatch.setattr(ruta, "probabilidades_legales", probabilidades)
    monkeypatch.setattr(ruta, "calcular_saliencia", lambda fen: [0.0] * 64)
    monkeypatch.setattr(ruta, "calcular_atencion", lambda fen: [])
    monkeypatch.setattr(
        ruta, "explicar_top_candidatas",
        lambda fen: [{"jugada": red_prefiere, "probabilidad": 0.7, "da_jaque_mate": False,
                      "rival_tiene_mate_en_1": False, "pieza_colgada": False, "elegida": True}],
    )
    monkeypatch.setattr(ruta, "analizar_posicion", lambda fen, nivel, tiempo_limite: {"jugada": "Kd1", "evaluacion_cp": 0})
    return TestClient(app)


def test_la_inferencia_expone_el_calculo_y_la_jugada_que_corrige_a_la_red(monkeypatch) -> None:
    monkeypatch.delenv("AJEDREZ_TURING_PROFUNDIDAD", raising=False)
    cliente = _cliente_con_red_de_mentira(monkeypatch, red_prefiere="Qd4")  # Qd4?? regala la dama

    cuerpo = cliente.post("/aprendizaje/inferencia", json={"fen": "4k3/8/8/4p3/8/8/3Q4/4K3 w - - 0 1"}).json()

    assert cuerpo["calculo"]["jugada_red_sola"] == "Qd4" and cuerpo["calculo"]["corrige_a_la_red"]
    assert cuerpo["jugada_elegida"] != "Qd4" and cuerpo["jugada_elegida"] == cuerpo["calculo"]["candidatas"][0]["jugada"]
    assert [c["elegida"] for c in cuerpo["calculo"]["candidatas"]].count(True) == 1
    assert cuerpo["candidatas_detalladas"][0]["elegida"] is False  # la red proponía Qd4, pero no se juega


def test_con_la_busqueda_desactivada_la_inferencia_no_trae_calculo(monkeypatch) -> None:
    monkeypatch.setenv("AJEDREZ_TURING_PROFUNDIDAD", "0")
    cliente = _cliente_con_red_de_mentira(monkeypatch, red_prefiere="Qd4")

    cuerpo = cliente.post("/aprendizaje/inferencia", json={"fen": "4k3/8/8/4p3/8/8/3Q4/4K3 w - - 0 1"}).json()

    assert cuerpo["calculo"] is None and cuerpo["jugada_elegida"] == "Qd4"
