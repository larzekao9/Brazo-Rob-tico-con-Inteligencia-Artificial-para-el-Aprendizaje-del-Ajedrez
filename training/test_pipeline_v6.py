"""Pipeline de la v6: conteo por ELO, extracción compacta con validación por partida y filtro de ELO en la evaluación."""
from pathlib import Path

import numpy as np
import pytest
import zstandard as zstd

from training.data_pipeline import contar_partidas_por_elo, pgn_a_muestras_divididas
from training.evaluar_modelo import partidas_desde


def _partida(blancas: int | None, negras: int | None, jugadas: str) -> str:
    elo_b = f'[WhiteElo "{blancas}"]\n' if blancas is not None else ""
    elo_n = f'[BlackElo "{negras}"]\n' if negras is not None else ""
    return f'[Event "Test"]\n{elo_b}{elo_n}[Result "1-0"]\n\n{jugadas} 1-0\n\n'


# 6 partidas: tres de maestros (2450/2500, 2300/2350, 2100/2600), una mixta, una débil y una sin ELO.
PARTIDAS = [
    _partida(2450, 2500, "1. e4 e5 2. Nf3 Nc6"),
    _partida(2300, 2350, "1. d4 d5 2. c4 e6"),
    _partida(2100, 2600, "1. c4 e5 2. Nc3 Nf6"),
    _partida(2500, 1500, "1. e4 c5 2. Nf3 d6"),
    _partida(1400, 1500, "1. e4 e5 2. Bc4 Nf6"),
    _partida(None, None, "1. e4 e6 2. d4 d5"),
]


@pytest.fixture
def dataset(tmp_path) -> Path:
    ruta = tmp_path / "partidas.pgn.zst"
    with open(ruta, "wb") as archivo, zstd.ZstdCompressor().stream_writer(archivo) as flujo:
        flujo.write("".join(PARTIDAS).encode("utf-8"))
    return ruta


def test_contar_partidas_por_elo_cuenta_solo_las_que_tienen_ambos_jugadores_arriba_del_umbral(dataset) -> None:
    conteo = contar_partidas_por_elo(dataset, umbrales=(2000, 2200, 2400))

    assert conteo["leidas"] == 6
    assert conteo["con_elo"] == 5  # la sexta no trae ELO
    # Con ambos jugadores arriba: 2450/2500, 2300/2350 y 2100/2600 pasan 2000; solo las dos primeras pasan 2200;
    # solo 2450/2500 pasa 2400. La mixta (2500/1500) no cuenta en ningún umbral.
    assert conteo["por_umbral"] == {2000: 3, 2200: 2, 2400: 1}


def test_contar_partidas_por_elo_respeta_el_limite_de_lectura(dataset) -> None:
    conteo = contar_partidas_por_elo(dataset, umbrales=(2000,), limite_leidas=2)

    assert conteo["leidas"] == 2 and conteo["por_umbral"] == {2000: 2}


def test_la_extraccion_divide_por_partida_y_guarda_uint8(dataset) -> None:
    resultado = pgn_a_muestras_divididas(dataset, limite_partidas=10, elo_minimo=2000, fraccion_validacion=0.5, semilla=1)

    assert resultado.partidas_train + resultado.partidas_val == 3  # las 3 partidas con ambos >= 2000
    assert len(resultado.muestras_train) + len(resultado.muestras_val) == 3 * 4  # 4 jugadas por partida
    tensor, etiqueta = (resultado.muestras_train or resultado.muestras_val)[0]
    assert tensor.dtype == np.uint8 and tensor.shape == (8, 8, 12) and 0 <= etiqueta < 4096
    assert tensor.max() == 1 and tensor.sum() == 32  # posición inicial: 32 piezas


def test_la_misma_partida_nunca_queda_en_train_y_en_val(dataset) -> None:
    resultado = pgn_a_muestras_divididas(dataset, limite_partidas=10, elo_minimo=2000, fraccion_validacion=0.5, semilla=3)

    # Cada partida de la fixture tiene 4 jugadas: los bloques de 4 muestras consecutivas son de una sola partida.
    assert len(resultado.muestras_train) % 4 == 0 and len(resultado.muestras_val) % 4 == 0
    assert resultado.partidas_train * 4 == len(resultado.muestras_train)
    assert resultado.partidas_val * 4 == len(resultado.muestras_val)


def test_la_asignacion_a_validacion_es_reproducible_con_la_misma_semilla(dataset) -> None:
    a = pgn_a_muestras_divididas(dataset, 10, 2000, fraccion_validacion=0.5, semilla=7)
    b = pgn_a_muestras_divididas(dataset, 10, 2000, fraccion_validacion=0.5, semilla=7)

    assert (a.partidas_train, a.partidas_val) == (b.partidas_train, b.partidas_val)
    assert [e for _, e in a.muestras_val] == [e for _, e in b.muestras_val]


def test_la_extraccion_informa_hasta_donde_leyo_para_poder_evaluar_con_partidas_nuevas(dataset) -> None:
    resultado = pgn_a_muestras_divididas(dataset, limite_partidas=2, elo_minimo=2000)

    # Aceptó las partidas 1 y 2 (ambas de maestros): leyó 2 del archivo.
    assert resultado.partidas_crudas_leidas == 2
    # Saltando las 3 primeras quedan 3 partidas y ninguna cumple ELO: las lee todas igual (3 saltadas + 3 leídas).
    saltando = pgn_a_muestras_divididas(dataset, limite_partidas=1, elo_minimo=2000, saltar_partidas=3)
    assert saltando.partidas_crudas_leidas == 6
    assert saltando.partidas_train + saltando.partidas_val == 0


def test_la_extraccion_respeta_el_limite_de_partidas_aceptadas(dataset) -> None:
    resultado = pgn_a_muestras_divididas(dataset, limite_partidas=1, elo_minimo=2000, fraccion_validacion=0.0)

    assert resultado.partidas_train == 1 and resultado.partidas_val == 0 and len(resultado.muestras_train) == 4


def test_la_evaluacion_puede_quedarse_solo_con_partidas_de_maestros(dataset) -> None:
    todas = list(partidas_desde(dataset, saltar_partidas=0, cantidad_partidas=10))
    maestros = list(partidas_desde(dataset, saltar_partidas=0, cantidad_partidas=10, elo_minimo=2200))

    assert len(todas) == 6 and len(maestros) == 2
