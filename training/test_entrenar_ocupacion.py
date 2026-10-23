"""Muestras del clasificador de ocupación: las vacías seguras cercanas a una pieza (`entrenar_ocupacion.vacias_cercanas`, `_cargar_base`)."""
import numpy as np

import training.capturar_dataset_propio as capturar
from training import entrenar_ocupacion


def test_vacias_cercanas_son_las_que_estan_a_dos_casillas_o_menos() -> None:
    datos = {"etiquetas": {"e4": "white-pawn"}, "vacias_seguras": ["e5", "g6", "h7", "e2", "a1", "c4"]}
    assert entrenar_ocupacion.vacias_cercanas(datos) == ["e5", "g6", "e2", "c4"]
    assert entrenar_ocupacion.vacias_cercanas({"etiquetas": {"e4": "white-pawn"}}) == []  # captura vieja, sin vacías seguras


def test_cargar_base_suma_las_vacias_cercanas_solo_si_la_captura_sigue(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import dataset_propio, geometria3d
    from backend.servicios.vision.test_validacion_orientacion import ESQUINAS, foto_con_piezas

    dataset = tmp_path / "dataset_propio"
    monkeypatch.setattr(capturar, "CARPETA_DATASET", dataset)
    monkeypatch.setattr(capturar, "esquinas_y_margen", lambda imagen, *a, **k: (ESQUINAS, 0.0))
    monkeypatch.setattr(entrenar_ocupacion, "CARPETA_DATASET_PROPIO", dataset)
    monkeypatch.setattr(geometria3d.tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    captura_id, _ = capturar.capturar_muestras_con_id("8/8/8/8/4P3/8/8/8", imagen=foto_con_piezas({"e4": "white-pawn"}), solo_piezas=True)

    muestras = entrenar_ocupacion._cargar_base()
    clases = [clase for _, clase, _ in muestras]
    assert clases.count("blanca") == 1 and clases.count("vacia") == 24  # 5 × 5 alrededor de e4, menos e4
    assert all(r.shape == muestras[0][0].shape for r, _, _ in muestras) and isinstance(muestras[0][0], np.ndarray)

    monkeypatch.setattr(dataset_propio, "_carpeta", lambda: dataset)
    dataset_propio.borrar_captura(captura_id)
    assert entrenar_ocupacion._cargar_base() == []  # deshecha: tampoco se usan sus vacías
