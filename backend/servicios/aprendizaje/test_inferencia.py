"""Test de inferencia (HU4) — no depende del checkpoint real (26MB, vive en
`training/checkpoints/`, ignorado por git): genera uno chico con pesos sin
entrenar para probar que `cargar_modelo`/`predecir_jugada` funcionan de punta
a punta. La precisión del modelo real se evalúa aparte (ver `docs/plan_sprints.md`).

Se salta automáticamente si `torch` no está instalado (ver test_modelo_jugadas.py).
"""
import chess
import pytest

torch = pytest.importorskip("torch")

from backend.servicios.aprendizaje.inferencia import cargar_modelo, predecir_jugada  # noqa: E402
from backend.servicios.aprendizaje.modelo_jugadas import NUM_CLASES, RedPrediccionJugadas  # noqa: E402


@pytest.fixture
def checkpoint_de_prueba(tmp_path):
    ruta = tmp_path / "checkpoint_prueba.pt"
    torch.save({"state_dict": RedPrediccionJugadas().state_dict(), "num_clases": NUM_CLASES}, ruta)
    return ruta


def test_cargar_modelo_devuelve_red_en_modo_eval(checkpoint_de_prueba):
    modelo = cargar_modelo(checkpoint_de_prueba)
    assert isinstance(modelo, RedPrediccionJugadas)
    assert not modelo.training


def test_predecir_jugada_devuelve_una_jugada_legal(checkpoint_de_prueba):
    tablero = chess.Board()
    jugada = predecir_jugada(tablero.fen(), checkpoint_de_prueba)
    assert jugada in [tablero.san(m) for m in tablero.legal_moves]


def test_predecir_jugada_sin_jugadas_legales_falla(checkpoint_de_prueba):
    fen_ahogado = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    with pytest.raises(ValueError):
        predecir_jugada(fen_ahogado, checkpoint_de_prueba)
