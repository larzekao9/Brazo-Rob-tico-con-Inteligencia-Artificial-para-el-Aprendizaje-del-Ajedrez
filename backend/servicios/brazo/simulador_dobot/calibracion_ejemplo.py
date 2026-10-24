"""Calibración y parámetros de agarre de EJEMPLO para arrancar el simulador sin el `brazo.json` real del usuario.

El tablero queda a unos 400 mm delante de la base, con casillas de 30,5 mm y la herramienta como en la prueba real (`rx = -180`,
`ry = 0`, `rz = -120`, `z_tope = 223,65`). Las aperturas por pieza son estimaciones coherentes con las formas de `parametros.py`.
"""
from __future__ import annotations

from pathlib import Path

from backend.servicios.brazo.calibracion_brazo import (
    CalibracionBrazo,
    ParametrosAgarre,
    construir_calibracion,
    guardar_calibracion_brazo,
    guardar_parametros_agarre,
)
from backend.servicios.brazo.simulador_dobot import cinematica

PASO_CASILLA_MM = 30.5
ORIGEN_A1 = (300.0, -3.5 * PASO_CASILLA_MM)
Z_ENSENANZA = 234.8
Z_TOPE_EJEMPLO = 223.65
X_CEMENTERIO = 300.0 + 7 * PASO_CASILLA_MM + 60.0  # 60 mm más allá de la fila 8
POSE_CERO = (250.0, -250.0, Z_TOPE_EJEMPLO + 250.0, -180.0, 0.0, -120.0)


def _puntos() -> dict[str, tuple[float, ...]]:
    x0, y0 = ORIGEN_A1
    orientacion = (-180.0, 0.0, -120.0)
    return {
        "a1": (x0, y0, Z_ENSENANZA, *orientacion),
        "h1": (x0, y0 + 7 * PASO_CASILLA_MM, Z_ENSENANZA, *orientacion),
        "a8": (x0 + 7 * PASO_CASILLA_MM, y0, Z_ENSENANZA, *orientacion),
        "h8": (x0 + 7 * PASO_CASILLA_MM, y0 + 7 * PASO_CASILLA_MM, Z_ENSENANZA, *orientacion),
    }


def angulos_cero_ejemplo() -> tuple[float, ...]:
    """Ángulos del modelo esquemático para la posición cero de ejemplo."""
    angulos = cinematica.angulos_para_pose(POSE_CERO[0], POSE_CERO[1], POSE_CERO[2], POSE_CERO[5])
    assert angulos is not None
    return angulos


def calibracion_ejemplo() -> CalibracionBrazo:
    """Calibración del tablero de ejemplo."""
    return construir_calibracion(angulos_cero_ejemplo(), _puntos())


def parametros_agarre_ejemplo() -> ParametrosAgarre:
    """Parámetros de agarre de ejemplo (fuerza 40 %, pinza al 20 %, aperturas de bajada por pieza)."""
    return ParametrosAgarre(
        z_tope=Z_TOPE_EJEMPLO,
        aperturas_por_pieza={"n": 860, "b": 760, "r": 760, "q": 800, "k": 800},
        fuerza=40,
        velocidad_pinza=20,
        # Cementerio y damas de reserva pasada la octava fila (x mayor que la de a8), a la altura del tablero.
        cementerio_origen=[X_CEMENTERIO, -100.0],
        cementerio_paso=[0.0, 33.0],
        cementerio_paso_fila=[33.0, 0.0],
        cementerio_columnas=8,
        reservas={"dama_blanca": [X_CEMENTERIO - 20, -150.0], "dama_negra": [X_CEMENTERIO - 20, -185.0]},
    )


def escribir_calibracion_ejemplo(ruta: Path) -> Path:
    """Escribe la calibración y los parámetros de ejemplo en `ruta` (formato de `brazo.json`) para usar con `CALIBRACION_BRAZO_ARCHIVO`."""
    ruta = Path(ruta)
    guardar_calibracion_brazo(angulos_cero_ejemplo(), _puntos(), ruta)
    guardar_parametros_agarre(parametros_agarre_ejemplo(), ruta)
    return ruta
