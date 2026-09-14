"""Test básico de forma de la red de HU3 — no de precisión (para eso, ver el notebook de Colab).

Se salta automáticamente si `torch` no está instalado en esta máquina (el
entrenamiento real corre en Colab; no todas las máquinas del equipo necesitan
tenerlo instalado localmente, ver environment.yml).
"""
import chess
import pytest

torch = pytest.importorskip("torch")

from training.data_pipeline import board_to_tensor  # noqa: E402

from backend.servicios.aprendizaje.modelo_jugadas import (  # noqa: E402
    NUM_CLASES,
    RedPrediccionJugadas,
    tensor_a_entrada_red,
)


def test_tensor_a_entrada_red_permuta_a_canales_primero():
    tensor_posicion = board_to_tensor(chess.Board())
    entrada = tensor_a_entrada_red(tensor_posicion)
    assert tuple(entrada.shape) == (12, 8, 8)


def test_forward_devuelve_logits_por_lote():
    red = RedPrediccionJugadas()
    lote = torch.stack([tensor_a_entrada_red(board_to_tensor(chess.Board())) for _ in range(4)])
    salida = red(lote)
    assert tuple(salida.shape) == (4, NUM_CLASES)
