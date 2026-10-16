"""Red de valor y su entrenamiento: formas, métricas y una corrida mínima de punta a punta (sin descargar nada)."""
import math

import chess
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from backend.servicios.aprendizaje.busqueda_turing import evaluar  # noqa: E402
from backend.servicios.aprendizaje.modelo_valor import RedValor  # noqa: E402
from training.data_pipeline import board_to_tensor  # noqa: E402
from training.datos_valor import ESCALA_CP  # noqa: E402
from training.entrenar_valor import a_entrada, entrenar, metricas, valor_de_evaluacion_manual  # noqa: E402


def _posicion(fen: str) -> np.ndarray:
    return board_to_tensor(chess.Board(fen)).astype(np.uint8)


def test_la_red_devuelve_un_valor_por_posicion_entre_menos_uno_y_uno() -> None:
    red = RedValor(canales=16, bloques=1).eval()

    salida = red(torch.zeros(5, 12, 8, 8))

    assert salida.shape == (5,) and bool(((salida >= -1) & (salida <= 1)).all())


def test_a_entrada_pasa_a_el_formato_de_la_red() -> None:
    entrada = a_entrada(np.stack([_posicion(chess.STARTING_FEN)] * 3))

    assert entrada.shape == (3, 12, 8, 8) and entrada.dtype == torch.float32


def test_la_evaluacion_manual_reconstruida_coincide_con_evaluar_del_tablero() -> None:
    fens = [
        chess.STARTING_FEN,
        "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2QK2R b KQ - 0 9",  # mueven las negras
    ]
    posiciones = np.stack([_posicion(f) for f in fens])

    reconstruida = valor_de_evaluacion_manual(posiciones)

    esperada = [math.tanh(evaluar(chess.Board(f)) / ESCALA_CP) for f in fens]
    assert reconstruida == pytest.approx(esperada, abs=1e-6)


def test_metricas_de_una_prediccion_perfecta_y_de_una_inversa() -> None:
    objetivo = np.array([-0.9, -0.5, 0.0, 0.4, 0.8], dtype=np.float32)

    perfecta = metricas(objetivo, objetivo)
    inversa = metricas(-objetivo, objetivo)

    assert perfecta["error_cuadratico"] == 0 and perfecta["correlacion"] == pytest.approx(1.0) and perfecta["acierto_signo_claras"] == 1.0
    assert inversa["correlacion"] == pytest.approx(-1.0) and inversa["acierto_signo_claras"] == 0.0


def test_una_corrida_minima_entrena_guarda_el_checkpoint_y_compara_con_la_manual(tmp_path) -> None:
    # Posiciones sintéticas con un objetivo aprendible: quien tiene más material (visto desde quien mueve).
    rng = np.random.default_rng(1)
    fens = [chess.STARTING_FEN, "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1"]
    objetivos = {fens[0]: 0.0, fens[1]: 0.9, fens[2]: -0.9}
    elegidas = rng.integers(0, 3, size=300)
    ruta_datos = tmp_path / "datos.npz"
    np.savez(ruta_datos, posiciones=np.stack([_posicion(fens[i]) for i in elegidas]), valores=np.array([objetivos[fens[i]] for i in elegidas], dtype=np.float32))

    resultado = entrenar(ruta_datos, epocas=3, salida=tmp_path / "valor.pt", canales=8, bloques=1, lote=64)

    punto = torch.load(tmp_path / "valor.pt", map_location="cpu")
    assert punto["canales"] == 8 and punto["bloques"] == 1 and "state_dict" in punto
    assert set(resultado) == {"red", "manual"} and resultado["red"]["error_cuadratico"] < 1.0
