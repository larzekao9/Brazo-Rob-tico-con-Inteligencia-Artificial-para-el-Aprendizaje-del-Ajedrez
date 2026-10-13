"""Interfaz UCI de Turing: protocolo (con un decisor falso) y una prueba real contra `python-chess` si hay modelo."""
import io
import sys
from pathlib import Path

import chess
import chess.engine
import pytest

from training.turing_uci import MotorUCI, ejecutar

RAIZ = Path(__file__).resolve().parent.parent
CHECKPOINTS = sorted((RAIZ / "training" / "checkpoints").glob("modelo_jugadas_v*.pt"))


def _primera_legal(fen: str, nivel: int) -> str:
    tablero = chess.Board(fen)
    return tablero.san(next(iter(tablero.legal_moves)))


def _motor() -> MotorUCI:
    return MotorUCI(decidir=_primera_legal)


def test_uci_responde_con_su_nombre_y_opciones() -> None:
    respuesta = _motor().procesar("uci")

    assert "id name Turing" in respuesta and respuesta[-1] == "uciok"
    assert any(linea.startswith("option name Nivel") for linea in respuesta)
    assert any(linea.startswith("option name Checkpoint") for linea in respuesta)


def test_isready_responde_readyok() -> None:
    assert _motor().procesar("isready") == ["readyok"]


def test_go_en_la_posicion_inicial_devuelve_una_jugada_legal_en_formato_uci() -> None:
    motor = _motor()
    motor.procesar("position startpos")

    respuesta = motor.procesar("go movetime 1000")

    assert len(respuesta) == 1 and respuesta[0].startswith("bestmove ")
    assert chess.Move.from_uci(respuesta[0].split()[1]) in chess.Board().legal_moves


def test_position_aplica_las_jugadas_dadas() -> None:
    motor = _motor()

    motor.procesar("position startpos moves e2e4 e7e5 g1f3")

    assert motor.tablero.fen().startswith("rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b")


def test_position_con_fen_y_jugadas() -> None:
    motor = _motor()
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"

    motor.procesar(f"position fen {fen} moves f1b5")

    assert motor.tablero.piece_at(chess.B5) is not None and motor.tablero.turn == chess.BLACK


def test_position_con_jugada_ilegal_avisa_y_no_cambia_el_tablero() -> None:
    motor = _motor()
    motor.procesar("position startpos moves e2e4")

    respuesta = motor.procesar("position startpos moves e2e5")

    assert respuesta and respuesta[0].startswith("info string")
    assert len(motor.tablero.move_stack) == 1  # sigue la posición anterior


def test_go_sin_jugadas_legales_devuelve_0000() -> None:
    motor = _motor()
    motor.procesar("position fen 7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")  # ahogado: negras sin jugadas

    assert motor.procesar("go") == ["bestmove 0000"]


def test_ucinewgame_reinicia_el_tablero() -> None:
    motor = _motor()
    motor.procesar("position startpos moves e2e4")

    motor.procesar("ucinewgame")

    assert motor.tablero == chess.Board()


def test_setoption_cambia_el_nivel_con_limites() -> None:
    motor = _motor()

    motor.procesar("setoption name Nivel value 7")
    assert motor.nivel == 7
    motor.procesar("setoption name Nivel value 99")
    assert motor.nivel == 18
    motor.procesar("setoption name Nivel value -5")
    assert motor.nivel == 0


def test_setoption_acepta_rutas_con_espacios() -> None:
    motor = _motor()

    motor.procesar("setoption name Checkpoint value C:/mis modelos/v6.pt")

    assert motor.ruta_checkpoint == "C:/mis modelos/v6.pt"


def test_si_el_modelo_falla_igual_responde_con_una_jugada_legal() -> None:
    def roto(fen: str, nivel: int) -> str:
        raise RuntimeError("modelo no disponible")

    motor = MotorUCI(decidir=roto)
    motor.procesar("position startpos")

    respuesta = motor.procesar("go")

    assert respuesta[0].startswith("info string error del modelo") and respuesta[1].startswith("bestmove ")
    assert respuesta[1] != "bestmove 0000"


def test_comandos_desconocidos_se_ignoran() -> None:
    assert _motor().procesar("comando_inventado 1 2 3") == []
    assert _motor().procesar("") == []


def test_el_bucle_termina_con_quit() -> None:
    salida = io.StringIO()

    ejecutar(io.StringIO("uci\nisready\nquit\nisready\n"), salida, _motor())

    assert salida.getvalue().splitlines().count("readyok") == 1  # el isready posterior a quit no se atiende


@pytest.mark.skipif(not CHECKPOINTS, reason="no hay checkpoints de modelo en training/checkpoints")
def test_turing_juega_de_verdad_a_traves_de_python_chess() -> None:
    """Prueba de punta a punta: un proceso real de Turing hablando UCI con `python-chess`, con la red cargada."""
    motor = chess.engine.SimpleEngine.popen_uci(
        [sys.executable, "-m", "training.turing_uci", "--checkpoint", str(CHECKPOINTS[-1])], cwd=str(RAIZ), timeout=120
    )
    try:
        assert motor.id["name"] == "Turing"
        tablero = chess.Board()
        for _ in range(4):  # cuatro medias jugadas contra sí mismo
            resultado = motor.play(tablero, chess.engine.Limit(time=1))
            assert resultado.move in tablero.legal_moves
            tablero.push(resultado.move)
    finally:
        motor.quit()
