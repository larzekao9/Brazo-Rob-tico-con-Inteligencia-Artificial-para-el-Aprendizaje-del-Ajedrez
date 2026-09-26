"""Calibración del tablero físico contra el espacio de trabajo del Dobot (HU9).

Un tablero de ajedrez real es, para este propósito, una grilla plana 8x8 de
casillas de tamaño uniforme. Con 3 puntos de referencia medidos a mano en el
robot (ej. las casillas "a1", "h1" y "a8", que cubren ambos ejes del tablero)
alcanza para reconstruir por una transformación afín 2D la posición XYZ de las
64 casillas.

Esta asunción (tablero plano, casillas regulares) es razonable para un
tablero físico real, pero es una limitación conocida: si en la práctica el
tablero no está del todo nivelado, o las casillas no son perfectamente
uniformes, las coordenadas que devuelve `calcular_posiciones_casillas` van a
tener un margen de error que hay que verificar en el sitio — no es algo que
este módulo pueda corregir por sí solo.

No hay ninguna coordenada real hardcodeada acá: los `PuntoCalibracion` se
miden jogueando el brazo real en DobotStudio Pro y leyendo su posición
reportada (ver `docs/bitacora_brazo_robotico.md`, entrada de la prueba en la
universidad).
"""
from __future__ import annotations

from dataclasses import dataclass

import chess
import numpy as np


@dataclass
class PuntoCalibracion:
    """Un punto de referencia medido a mano en el Dobot real.

    `x`, `y`, `z` son las coordenadas que reporta el propio robot (vía
    DobotStudio o `_enviar_comando`), en milímetros — nunca estimadas.
    """

    casilla: str
    x: float
    y: float
    z: float


def calcular_posiciones_casillas(
    puntos: list[PuntoCalibracion],
) -> dict[str, tuple[float, float, float]]:
    """Calcula la posición XYZ real de las 64 casillas por transformación afín.

    Usa los 3 primeros elementos de `puntos` para resolver la transformación
    afín 2D (columna, fila) del tablero -> (x, y) real del Dobot, donde
    columna 0-7 corresponde a las columnas "a"-"h" y fila 0-7 a las filas
    "1"-"8" (ver `chess.square_file` / `chess.square_rank`). Para `z` usa el
    promedio de los `z` de **todos** los puntos de `puntos` (no solo los 3
    primeros), asumiendo el tablero plano.

    Args:
        puntos: puntos de referencia medidos a mano en el robot real (ver
            `PuntoCalibracion`). Se necesitan al menos 3, cubriendo ambos ejes
            del tablero (ej. "a1", "h1", "a8") para que la transformación no
            sea degenerada.

    Returns:
        Dict notación algebraica ("a1".."h8") -> (x, y, z) en mm.

    Raises:
        ValueError: si `puntos` tiene menos de 3 elementos, o si los 3
            primeros son colineales en el plano (columna, fila) del tablero y
            no alcanzan para resolver la transformación afín.
    """
    if len(puntos) < 3:
        raise ValueError(
            f"Se necesitan al menos 3 puntos de calibración, se recibieron {len(puntos)}"
        )

    columnas_filas = []
    for punto in puntos[:3]:
        casilla_idx = chess.parse_square(punto.casilla)
        columnas_filas.append((chess.square_file(casilla_idx), chess.square_rank(casilla_idx)))

    matriz_afin = np.array(
        [[columna, fila, 1.0] for columna, fila in columnas_filas]
    )
    vector_x = np.array([punto.x for punto in puntos[:3]])
    vector_y = np.array([punto.y for punto in puntos[:3]])

    try:
        coeficientes_x = np.linalg.solve(matriz_afin, vector_x)
        coeficientes_y = np.linalg.solve(matriz_afin, vector_y)
    except np.linalg.LinAlgError as error:
        raise ValueError(
            "Los 3 primeros puntos de calibración son colineales en el plano del "
            "tablero (columna, fila) y no alcanzan para resolver la transformación "
            "afín — usá 3 puntos que cubran ambos ejes, ej. 'a1', 'h1', 'a8'."
        ) from error

    altura_z = sum(punto.z for punto in puntos) / len(puntos)

    posiciones: dict[str, tuple[float, float, float]] = {}
    for columna in range(8):
        for fila in range(8):
            casilla = chess.square_name(chess.square(columna, fila))
            x = coeficientes_x[0] * columna + coeficientes_x[1] * fila + coeficientes_x[2]
            y = coeficientes_y[0] * columna + coeficientes_y[1] * fila + coeficientes_y[2]
            posiciones[casilla] = (float(x), float(y), float(altura_z))
    return posiciones
