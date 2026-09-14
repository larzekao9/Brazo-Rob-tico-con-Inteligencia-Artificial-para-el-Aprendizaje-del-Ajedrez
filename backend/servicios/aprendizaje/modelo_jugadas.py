"""Arquitectura de la red que predice la jugada humana a partir de una posición (HU3/HU4).

Vive acá (no en `training/`) por el mismo motivo que
`backend/servicios/vision/modelo_piezas.py`: tanto el entrenamiento
(`training/colab_entrenamiento.ipynb`) como la futura inferencia en
producción (`backend/servicios/aprendizaje/inferencia.py`, HU4) importan esta
misma definición, así ninguno de los dos depende del otro.

Codificación de entrada/salida compartida con `training/data_pipeline.py`:
tablero como tensor (8, 8, 12) en perspectiva del jugador a mover, jugada
como clase `origen*64 + destino` (4096 clases, sin distinguir subpromoción).
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

NUM_CLASES = 4096  # from_square * 64 + to_square, ver training/data_pipeline.py


def tensor_a_entrada_red(tensor_posicion: np.ndarray) -> torch.Tensor:
    """Convierte el tensor (8, 8, 12) de `board_to_tensor` al formato (12, 8, 8) de la red.

    Se comparte entre entrenamiento e inferencia para que ambos lados apliquen
    exactamente la misma conversión.
    """
    return torch.from_numpy(tensor_posicion).permute(2, 0, 1)


class RedPrediccionJugadas(nn.Module):
    """CNN chica: 3 bloques conv+batchnorm+relu y una cabeza lineal a `NUM_CLASES`.

    Primera versión deliberadamente simple (HU3): el objetivo es que el
    pipeline de entrenamiento funcione de punta a punta, no lograr precisión
    alta todavía (ver PLAN_IMPLEMENTACION_COMPLETO.md, sección 16). Sin
    pooling porque el tablero ya es chico (8x8) — reducirlo más perdería
    la posición exacta de las piezas, que es la señal principal acá.
    """

    def __init__(self, cantidad_clases: int = NUM_CLASES):
        super().__init__()
        self.caracteristicas = nn.Sequential(
            nn.Conv2d(12, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(128, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
        )
        self.clasificador = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 8 * 8, 512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, cantidad_clases),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.clasificador(self.caracteristicas(x))
