"""Enfrentamientos de partidas completas, con jugadores de mentira (sin red ni Stockfish)."""
import chess
import pytest

from training.enfrentar_modelos import (
    APERTURAS_UCI,
    Marcador,
    diferencia_elo,
    enfrentar,
    intervalo_elo,
    jugar_partida,
)


def _guion(*jugadas: str):
    """Jugador que juega una lista fija de jugadas en orden."""
    pendientes = list(jugadas)
    return lambda fen: pendientes.pop(0)


def _primera_legal(fen: str) -> str:
    tablero = chess.Board(fen)
    return tablero.san(next(iter(tablero.legal_moves)))


def test_el_mate_del_tonto_lo_gana_negras() -> None:
    resultado = jugar_partida(_guion("f3", "g4"), _guion("e5", "Qh4#"))

    assert resultado == "0-1"


def test_el_mate_pastor_lo_gana_blancas() -> None:
    resultado = jugar_partida(_guion("e4", "Bc4", "Qh5", "Qxf7#"), _guion("e5", "Nc6", "Nf6"))

    assert resultado == "1-0"


def test_una_jugada_ilegal_cuenta_como_derrota_de_quien_la_hizo() -> None:
    assert jugar_partida(_guion("e5"), _guion("e5")) == "0-1"  # blancas intentan e5 desde la posición inicial


def test_el_tope_de_jugadas_da_tablas() -> None:
    assert jugar_partida(_primera_legal, _primera_legal, max_jugadas=4) == "1/2-1/2"


def test_las_aperturas_se_aplican_antes_de_jugar() -> None:
    vistos = []

    def espia(fen: str) -> str:
        vistos.append(fen)
        return _primera_legal(fen)

    jugar_partida(espia, espia, "e2e4 e7e5", max_jugadas=3)

    assert vistos[0].split()[0] == "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR"  # ya con 1.e4 e5 jugado


def test_enfrentar_juega_cada_apertura_con_los_dos_colores() -> None:
    marcador = enfrentar(_primera_legal, _primera_legal, APERTURAS_UCI[:3])

    assert marcador.partidas == 6


def test_enfrentar_cuenta_a_favor_de_a_aunque_cambie_de_color() -> None:
    # A siempre juega la primera legal; B siempre juega jugadas ilegales: A gana las dos partidas con cada color.
    marcador = enfrentar(_primera_legal, lambda fen: "Zz9", APERTURAS_UCI[:2])

    assert (marcador.victorias_a, marcador.tablas, marcador.victorias_b) == (4, 0, 0)


def test_puntaje_y_elo() -> None:
    marcador = Marcador(victorias_a=6, tablas=2, victorias_b=2)

    assert marcador.puntaje_a == pytest.approx(0.7)
    assert diferencia_elo(0.5) == pytest.approx(0.0)
    assert diferencia_elo(0.7) == pytest.approx(147.19, abs=0.5)
    assert diferencia_elo(0.9) > diferencia_elo(0.7) > 0 > diferencia_elo(0.3)


def test_el_elo_no_se_va_al_infinito_con_puntajes_extremos() -> None:
    assert abs(diferencia_elo(1.0)) < 1000 and abs(diferencia_elo(0.0)) < 1000


def test_el_intervalo_contiene_al_valor_central_y_se_achica_con_mas_partidas() -> None:
    chico = Marcador(6, 2, 2)
    grande = Marcador(60, 20, 20)

    bajo, alto = intervalo_elo(chico)
    bajo_g, alto_g = intervalo_elo(grande)

    assert bajo < diferencia_elo(chico.puntaje_a) < alto
    assert (alto_g - bajo_g) < (alto - bajo)
