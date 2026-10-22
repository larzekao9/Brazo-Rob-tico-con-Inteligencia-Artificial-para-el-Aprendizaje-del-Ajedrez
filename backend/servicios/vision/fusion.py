"""Cómo se combinan las lecturas de las dos cámaras de un mismo tablero.

Se usa el PRODUCTO de las probabilidades de cada cámara, renormalizado (un "producto de expertos", que es sumar sus logaritmos): cuando las dos
cámaras coinciden en una clase, la confianza SUBE (con el promedio quedaba igual); cuando discrepan fuerte, ninguna clase se impone y la
confianza queda baja (menos de 0,5), lo que se muestra como dudoso. Además `casillas_en_desacuerdo` marca esas casillas. Es lo que conviene
con el error de la altura de las piezas: una pieza alta se inclina hacia lados distintos en cada cámara, así que la casilla vecina que una
cámara ve "ocupada" por la cabeza de la pieza, la otra suele verla vacía, y el desacuerdo queda a la vista en lugar de esconderse en un promedio.
"""
from __future__ import annotations

import numpy as np

EPSILON = 1e-3
"""Piso de probabilidad: evita que un cero absoluto de una cámara anule por completo a la otra (un solo cuadro ruidoso no decide)."""


def fusionar_probabilidades(lecturas: list[np.ndarray]) -> np.ndarray:
    """Producto, renormalizado por fila, de matrices `(casillas, clases)` de probabilidades (una por cámara)."""
    if not lecturas:
        raise ValueError("No hay lecturas que fusionar")
    if len(lecturas) == 1:
        return np.asarray(lecturas[0], dtype=np.float64)
    logaritmos = np.log(np.stack(lecturas).astype(np.float64) + EPSILON).sum(axis=0)
    fusion = np.exp(logaritmos)
    return fusion / fusion.sum(axis=1, keepdims=True)


def casillas_en_desacuerdo(lecturas: list[np.ndarray]) -> list[bool]:
    """Para cada casilla, `True` si no todas las cámaras coinciden en la clase más probable."""
    if len(lecturas) < 2:
        return [False] * len(lecturas[0])
    mejores = np.stack([np.argmax(lectura, axis=1) for lectura in lecturas])
    return [bool(len(set(columna)) > 1) for columna in mejores.T]
