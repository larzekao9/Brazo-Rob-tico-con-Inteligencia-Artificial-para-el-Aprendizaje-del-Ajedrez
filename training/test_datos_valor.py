"""Datos de la cabeza de valor: objetivos, lectura de la base de evaluaciones y armado del dataset (sin red: archivos locales)."""
import json
import math

import numpy as np
import pytest
import zstandard

from training.datos_valor import construir_dataset, cp_desde_valor, leer_evaluaciones, objetivo_valor

POSICION_INICIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"
NEGRAS_MUEVEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -"


def _registro(fen: str, cp: int | None = 30, mate: int | None = None, profundidad: int = 30) -> dict:
    linea = {"mate": mate, "line": "e2e4"} if mate is not None else {"cp": cp, "line": "e2e4"}
    return {"fen": fen, "evals": [{"pvs": [linea], "knodes": 1000, "depth": profundidad}]}


def _archivo(tmp_path, registros: list, extra: bytes = b"") -> str:
    texto = "\n".join(json.dumps(r) for r in registros).encode() + b"\n" + extra
    ruta = tmp_path / "evals.jsonl.zst"
    ruta.write_bytes(zstandard.ZstdCompressor().compress(texto))
    return str(ruta)


# --- objetivo de entrenamiento ----------------------------------------------------------------------------------------
def test_la_igualdad_vale_cero() -> None:
    assert objetivo_valor(0, None, True) == 0 and objetivo_valor(0, None, False) == 0


def test_el_valor_se_ve_desde_quien_mueve() -> None:
    # +150 para las blancas: bueno si mueven ellas, malo si mueven las negras (misma posición, otro turno).
    assert objetivo_valor(150, None, True) == pytest.approx(-objetivo_valor(150, None, False))
    assert objetivo_valor(150, None, True) > 0


def test_las_ventajas_grandes_saturan_cerca_de_uno() -> None:
    assert 0.99 < objetivo_valor(2000, None, True) <= 1.0
    assert objetivo_valor(100_000, None, True) == objetivo_valor(3000, None, True)  # se acota


def test_un_mate_vale_uno_con_el_signo_de_quien_lo_da() -> None:
    assert objetivo_valor(None, 5, True) == 1.0 and objetivo_valor(None, -3, True) == -1.0
    assert objetivo_valor(None, 5, False) == -1.0  # mate de las blancas, pero mueven las negras


def test_sin_cp_ni_mate_da_error() -> None:
    with pytest.raises(ValueError):
        objetivo_valor(None, None, True)


def test_cp_desde_valor_es_el_inverso_para_ventajas_normales() -> None:
    for cp in (-600, -80, 0, 35, 250, 900):
        assert cp_desde_valor(objetivo_valor(cp, None, True)) == pytest.approx(cp, abs=1e-6)
    assert cp_desde_valor(1.0) <= 3000 and cp_desde_valor(-1.0) >= -3000


# --- lectura de la base ----------------------------------------------------------------------------------------------
def test_lee_posiciones_con_su_valor_desde_quien_mueve(tmp_path) -> None:
    ruta = _archivo(tmp_path, [_registro(POSICION_INICIAL, cp=40), _registro(NEGRAS_MUEVEN, cp=40)])

    filas = list(leer_evaluaciones(ruta))

    assert [f[0].split()[1] for f in filas] == ["w", "b"] and all(f[0].endswith(" 0 1") for f in filas)
    assert filas[0][1] == pytest.approx(math.tanh(40 / 400)) and filas[1][1] == pytest.approx(-math.tanh(40 / 400))


def test_toma_la_evaluacion_de_mayor_profundidad(tmp_path) -> None:
    registro = {"fen": POSICION_INICIAL, "evals": [
        {"pvs": [{"cp": -500, "line": "e2e4"}], "knodes": 1, "depth": 22},
        {"pvs": [{"cp": 100, "line": "e2e4"}], "knodes": 9, "depth": 60},
    ]}

    assert next(leer_evaluaciones(_archivo(tmp_path, [registro])))[1] == pytest.approx(math.tanh(100 / 400))


def test_descarta_lo_poco_profundo_y_las_lineas_rotas(tmp_path) -> None:
    ruta = _archivo(tmp_path, [_registro(POSICION_INICIAL, profundidad=10), _registro(NEGRAS_MUEVEN)], extra=b"esto no es json\n")

    assert [f[0].split()[1] for f in leer_evaluaciones(ruta)] == ["b"]


def test_un_archivo_cortado_a_mitad_termina_sin_error(tmp_path) -> None:
    ruta = tmp_path / "cortado.jsonl.zst"
    completo = zstandard.ZstdCompressor().compress(("\n".join(json.dumps(_registro(POSICION_INICIAL)) for _ in range(2000)) + "\n").encode())
    ruta.write_bytes(completo[: len(completo) // 2])

    assert len(list(leer_evaluaciones(str(ruta)))) <= 2000  # lo que se alcance a leer, sin romper


# --- dataset ----------------------------------------------------------------------------------------------------------
def test_arma_el_dataset_con_la_forma_y_los_tipos_esperados(tmp_path) -> None:
    ruta = _archivo(tmp_path, [_registro(POSICION_INICIAL, cp=20), _registro(NEGRAS_MUEVEN, cp=-35), _registro(POSICION_INICIAL, mate=2)])
    salida = tmp_path / "salida" / "valor.npz"

    cantidad = construir_dataset(ruta, salida, maximo=10)

    datos = np.load(salida)
    assert cantidad == 3 and datos["posiciones"].shape == (3, 8, 8, 12) and datos["posiciones"].dtype == np.uint8
    assert datos["valores"].dtype == np.float32 and datos["valores"][2] == 1.0 and set(np.unique(datos["posiciones"])) <= {0, 1}


def test_respeta_el_maximo_y_el_salto(tmp_path) -> None:
    ruta = _archivo(tmp_path, [_registro(POSICION_INICIAL, cp=i) for i in range(10)])

    assert construir_dataset(ruta, tmp_path / "a.npz", maximo=4) == 4
    assert construir_dataset(ruta, tmp_path / "b.npz", maximo=100, salto=3) == 4  # posiciones 0, 3, 6, 9


def test_sin_datos_da_error_claro(tmp_path) -> None:
    ruta = _archivo(tmp_path, [_registro(POSICION_INICIAL, profundidad=5)])

    with pytest.raises(RuntimeError):
        construir_dataset(ruta, tmp_path / "vacio.npz", maximo=10)
