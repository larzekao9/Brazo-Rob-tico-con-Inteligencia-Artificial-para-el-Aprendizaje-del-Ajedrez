"""Lanza la ventana 3D de PyBullet (`ver_partida_en_vivo.py`) como proceso aparte.

Sirve al botón "Ver en 3D" de la Sala de Control (frontend): un navegador no
puede abrir una ventana nativa, así que el backend lanza el proceso por él.
Ese script necesita el intérprete del entorno conda `ajedrez` (tiene pybullet
real instalado), que es distinto del intérprete que corre este backend — ver
`environment.yml` para cómo armar ese entorno en una máquina nueva.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from backend.servicios.partida.servicio_partida import obtener_partida

RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent.parent.parent

PYTHON_SIMULACION = os.environ.get(
    "AJEDREZ_PYTHON_SIMULACION",
    r"C:\Users\USUARIO\miniconda3\envs\ajedrez\python.exe",
)


def lanzar_ventana_3d(partida_id: str, token: str) -> None:
    """Abre la ventana PyBullet en vivo para `partida_id`, en un proceso aparte.

    No espera a que el proceso termine (`Popen`, no `run`) — la ventana queda
    corriendo hasta que el usuario la cierra. El proceso hijo hereda la
    consola del backend (no se captura su stdout/stderr), así que esta
    función vuelve de inmediato.

    Raises:
        KeyError: si no existe una partida con ese id (delega en
            `obtener_partida`, para no lanzar una ventana que va a fallar
            enseguida contra un id inventado).
        FileNotFoundError: si el intérprete del entorno conda `ajedrez` no
            existe en esta máquina (entorno de simulación no armado todavía).
    """
    obtener_partida(partida_id)
    if not Path(PYTHON_SIMULACION).is_file():
        raise FileNotFoundError(
            f"Entorno de simulación no encontrado: no existe '{PYTHON_SIMULACION}'. "
            "Revisá environment.yml y armá el entorno conda 'ajedrez' en esta máquina, "
            "o seteá la variable de entorno AJEDREZ_PYTHON_SIMULACION con la ruta correcta."
        )
    subprocess.Popen(
        [
            PYTHON_SIMULACION,
            "-m",
            "backend.servicios.simulacion.ver_partida_en_vivo",
            partida_id,
            token,
        ],
        cwd=str(RAIZ_REPOSITORIO),
    )
