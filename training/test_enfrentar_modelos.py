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


# --- Estimación de ELO contra rivales de ELO conocido -----------------------------------------------------------------
from training.enfrentar_modelos import estimar_elo  # noqa: E402


def test_si_empata_en_todo_el_elo_estimado_es_el_del_rival() -> None:
    estimacion, bajo, alto = estimar_elo([(1500, Marcador(10, 0, 10))])

    assert estimacion == pytest.approx(1500, abs=1)
    assert bajo < 1500 < alto


def test_con_varios_rivales_la_estimacion_queda_entre_ellos() -> None:
    # Gana mucho a 1320, pierde mucho a 1700: su nivel está en el medio.
    estimacion, bajo, alto = estimar_elo([(1320, Marcador(16, 2, 2)), (1500, Marcador(8, 4, 8)), (1700, Marcador(2, 2, 16))])

    assert 1450 < estimacion < 1550
    assert bajo < estimacion < alto


def test_si_gana_el_70_por_ciento_el_elo_es_unos_150_puntos_mayor() -> None:
    estimacion, _, _ = estimar_elo([(1500, Marcador(70, 0, 30))])

    assert estimacion == pytest.approx(1500 + 147, abs=3)


def test_si_pierde_todo_la_estimacion_queda_acotada_por_debajo_del_rival() -> None:
    estimacion, _, alto = estimar_elo([(1320, Marcador(0, 0, 20)), (1500, Marcador(0, 0, 20))])

    assert estimacion < 1320 and alto < 1320 + 900


def test_el_intervalo_se_achica_con_mas_partidas() -> None:
    _, bajo_c, alto_c = estimar_elo([(1500, Marcador(7, 0, 3))])
    _, bajo_g, alto_g = estimar_elo([(1500, Marcador(70, 0, 30))])

    assert (alto_g - bajo_g) < (alto_c - bajo_c)


def test_estimar_elo_sin_partidas_da_error() -> None:
    with pytest.raises(ValueError):
        estimar_elo([(1500, Marcador())])


# --- Stockfish que se cuelga a mitad de una medición larga -----------------------------------------------------------
class _MotorFalso:
    """Motor de mentira: falla las primeras `fallos` veces y después juega e2e4."""

    def __init__(self, fallos: int) -> None:
        self.fallos = fallos
        self.cerrado = False

    def play(self, tablero, limite):
        if self.fallos > 0:
            self.fallos -= 1
            raise TimeoutError
        return type("Resultado", (), {"move": chess.Move.from_uci("e2e4")})()

    def close(self) -> None:
        self.cerrado = True


def _stockfish_falso(fallos_por_motor: list[int]):
    from training.enfrentar_modelos import JugadorStockfish

    jugador = JugadorStockfish.__new__(JugadorStockfish)
    motores: list[_MotorFalso] = []

    def abrir() -> None:
        jugador._motor = _MotorFalso(fallos_por_motor.pop(0))
        motores.append(jugador._motor)

    jugador._abrir_motor = abrir
    jugador._limite = None
    abrir()
    return jugador, motores


def test_stockfish_colgado_se_reinicia_y_sigue_jugando() -> None:
    jugador, motores = _stockfish_falso([1, 0])  # el primer motor se cuelga una vez; el reiniciado anda

    assert jugador(chess.STARTING_FEN) == "e4"
    assert len(motores) == 2 and motores[0].cerrado


def test_stockfish_que_nunca_responde_termina_dando_error() -> None:
    jugador, _ = _stockfish_falso([1, 1, 1])

    with pytest.raises(TimeoutError):
        jugador(chess.STARTING_FEN)
