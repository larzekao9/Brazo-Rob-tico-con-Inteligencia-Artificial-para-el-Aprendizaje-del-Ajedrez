from pathlib import Path

import pytest

from training.evaluar_modelo import clasificar_perdida_cp, evaluar_modelo

DATASET_REAL = Path(__file__).resolve().parent / "data" / "lichess_db_standard_rated_2017-02.pgn.zst"


@pytest.mark.parametrize(
    "perdida_cp,balde_esperado",
    [
        (0, "aceptable"),
        (49, "aceptable"),
        (50, "imprecision"),
        (99, "imprecision"),
        (100, "error"),
        (299, "error"),
        (300, "blunder"),
    ],
)
def test_clasificar_perdida_cp(perdida_cp: int, balde_esperado: str) -> None:
    assert clasificar_perdida_cp(perdida_cp) == balde_esperado


@pytest.mark.skipif(not DATASET_REAL.exists(), reason="dataset de Lichess no descargado")
def test_evaluar_modelo_con_checkpoint_de_mentira(tmp_path) -> None:
    torch = pytest.importorskip("torch")
    from backend.servicios.aprendizaje.modelo_jugadas import NUM_CLASES, RedPrediccionJugadas

    ruta_checkpoint = tmp_path / "checkpoint_prueba.pt"
    torch.save({"state_dict": RedPrediccionJugadas().state_dict(), "num_clases": NUM_CLASES}, ruta_checkpoint)

    resultado = evaluar_modelo(
        DATASET_REAL,
        cantidad_partidas=2,
        saltar_partidas=0,
        ruta_checkpoint=ruta_checkpoint,
        tiempo_limite_stockfish=0.05,
    )

    assert resultado.total_jugadas > 0
    assert 0.0 <= resultado.accuracy <= 1.0
    assert sum(resultado.distribucion_errores.values()) == resultado.total_jugadas - resultado.aciertos
