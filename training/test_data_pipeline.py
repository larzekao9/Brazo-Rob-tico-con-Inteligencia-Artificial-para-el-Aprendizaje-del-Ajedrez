import io
from pathlib import Path

import chess
import chess.pgn
import pytest
import zstandard as zstd

from training.data_pipeline import board_to_tensor, jugada_a_etiqueta, pgn_to_samples

PGN_DOS_PARTIDAS = """\
[Event "Test"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0

[Event "Test"]
[Result "0-1"]

1. d4 d5 2. c4 e6 0-1

"""

DATASET_REAL = (
    Path(__file__).resolve().parent.parent
    / "training"
    / "data"
    / "lichess_db_standard_rated_2017-02.pgn.zst"
)


@pytest.fixture
def dataset_zst_chico(tmp_path) -> Path:
    ruta = tmp_path / "partidas.pgn.zst"
    compresor = zstd.ZstdCompressor()
    with open(ruta, "wb") as archivo, compresor.stream_writer(archivo) as flujo:
        flujo.write(PGN_DOS_PARTIDAS.encode("utf-8"))
    return ruta


def test_board_to_tensor_tiene_la_forma_esperada() -> None:
    tablero = chess.Board()
    tensor = board_to_tensor(tablero)
    assert tensor.shape == (8, 8, 12)
    assert tensor.sum() == 32  # las 32 piezas de la posición inicial


def test_board_to_tensor_posicion_inicial_es_simetrica_para_ambos_colores() -> None:
    blancas = board_to_tensor(chess.Board())
    tablero_negras = chess.Board()
    tablero_negras.push(chess.Move.from_uci("e2e4"))
    negras = board_to_tensor(tablero_negras)
    # Ambas posiciones son "mis piezas en las dos filas más cercanas a mí"
    assert blancas[0:2, :, 0:6].sum() == 16
    assert negras[0:2, :, 0:6].sum() == 16


def test_jugada_a_etiqueta_es_coherente_con_from_square_to_square() -> None:
    tablero = chess.Board()
    jugada = chess.Move.from_uci("e2e4")
    etiqueta = jugada_a_etiqueta(tablero, jugada)
    # Con blancas a mover no hay rotación: e2=12, e4=28
    assert etiqueta == chess.E2 * 64 + chess.E4


def test_pgn_to_samples_extrae_pares_tensor_etiqueta(dataset_zst_chico: Path) -> None:
    muestras = pgn_to_samples(dataset_zst_chico, limite_partidas=2)
    assert len(muestras) == 8  # 4 jugadas x 2 partidas
    for tensor, etiqueta in muestras:
        assert tensor.shape == (8, 8, 12)
        assert 0 <= etiqueta < 4096


def test_pgn_to_samples_respeta_el_limite_de_partidas(dataset_zst_chico: Path) -> None:
    muestras = pgn_to_samples(dataset_zst_chico, limite_partidas=1)
    assert len(muestras) == 4  # solo la primera partida (1.e4 e5 2.Nf3 Nc6)


@pytest.mark.skipif(not DATASET_REAL.exists(), reason="dataset de Lichess no descargado")
def test_pgn_to_samples_funciona_con_el_dataset_real_de_lichess() -> None:
    muestras = pgn_to_samples(DATASET_REAL, limite_partidas=5)
    assert len(muestras) > 0
    for tensor, etiqueta in muestras:
        assert tensor.shape == (8, 8, 12)
        assert 0 <= etiqueta < 4096
