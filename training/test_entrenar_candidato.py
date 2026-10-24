"""Partes puras del entrenamiento del candidato: qué fotos son de la misma posición de cámara y cómo se degradan las nítidas."""
import random

import numpy as np

from training.entrenar_candidato import degradar, fuerza_para_igualar, nitidez
from training.entrenar_piezas_propio import cenital, misma_posicion

ESQUINAS = np.array([[440.0, 588.0], [433.0, 291.0], [726.0, 284.0], [736.0, 584.0]])


def test_misma_posicion_tolera_volver_a_marcar_pero_no_mover_la_camara() -> None:
    assert misma_posicion(ESQUINAS + [4.0, -3.0], ESQUINAS)  # esquinas afinadas unos píxeles
    assert not misma_posicion(ESQUINAS + [90.0, 0.0], ESQUINAS)  # la cámara o el tablero se movieron


def test_cenital_es_1_de_frente_y_baja_con_la_inclinacion() -> None:
    cuadrado = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=float)
    trapecio = np.array([[20, 0], [80, 0], [100, 100], [0, 100]], dtype=float)
    assert cenital(cuadrado) == 1.0 and cenital(trapecio) < 0.7


def test_degradar_baja_la_nitidez_y_el_ajuste_la_iguala_al_objetivo() -> None:
    azar = np.random.default_rng(1)
    nitidas = [azar.integers(0, 255, (96, 96, 3), dtype=np.uint8) for _ in range(12)]  # mucho detalle
    original = float(np.median([nitidez(i) for i in nitidas]))
    objetivo = original * 0.6
    fuerza = fuerza_para_igualar(nitidas, objetivo)
    degradadas = [degradar(i, fuerza, random.Random(3)) for i in nitidas]
    assert 0 < fuerza <= 0.5 and float(np.median([nitidez(i) for i in degradadas])) < original
    assert all(d.shape == i.shape for d, i in zip(degradadas, nitidas))
