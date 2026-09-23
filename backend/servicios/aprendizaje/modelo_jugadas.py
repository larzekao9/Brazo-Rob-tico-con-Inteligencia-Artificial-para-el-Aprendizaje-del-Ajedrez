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


class BloqueResidual(nn.Module):
    """Bloque residual estándar de 2 convoluciones 3x3 con Batch Normalization y conexión skip.

    Permite a la red aprender relaciones tácticas profundas (rayos X, clavadas, diagonales)
    sin que se desvanezca el gradiente, siguiendo el diseño probado de AlphaZero / Leela Chess Zero.
    """

    def __init__(self, canales: int):
        super().__init__()
        self.conv1 = nn.Conv2d(canales, canales, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(canales)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(canales, canales, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(canales)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + residual
        return self.relu(out)


class RedResNetAjedrez(nn.Module):
    """Arquitectura ResNet moderna para ajedrez (v3).

    Consta de una capa de entrada para expandir los 12 canales del tablero a `canales`,
    una torre de N bloques residuales y una cabeza de política proyectada a las 4096 clases
    de jugadas posibles.
    """

    def __init__(
        self,
        canales: int = 128,
        cantidad_bloques: int = 4,
        cantidad_clases: int = NUM_CLASES,
    ):
        super().__init__()
        self.entrada = nn.Sequential(
            nn.Conv2d(12, canales, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(canales),
            nn.ReLU(inplace=True),
        )
        self.torre_residual = nn.Sequential(
            *[BloqueResidual(canales) for _ in range(cantidad_bloques)]
        )
        self.cabeza_politica = nn.Sequential(
            nn.Conv2d(canales, 32, kernel_size=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(32 * 8 * 8, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, cantidad_clases),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.entrada(x)
        x = self.torre_residual(x)
        return self.cabeza_politica(x)


class BloqueSE(nn.Module):
    """Mecanismo de atención por canales (Squeeze-and-Excitation).

    Permite a la red aprender a priorizar canales específicos según el contexto del
    tablero (ej. atención máxima a casillas del rey en jaque o torres en columnas abiertas),
    emulando la atención selectiva de un jugador experimentado.
    """

    def __init__(self, canales: int, reduccion: int = 8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(canales, canales // reduccion, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(canales // reduccion, canales, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        pesos = self.fc(x).view(b, c, 1, 1)
        return x * pesos


class BloqueResidualSE(nn.Module):
    """Bloque residual con atención por canales (SE-ResNet)."""

    def __init__(self, canales: int, reduccion: int = 8):
        super().__init__()
        self.conv1 = nn.Conv2d(canales, canales, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(canales)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(canales, canales, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(canales)
        self.se = BloqueSE(canales, reduccion=reduccion)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.se(out)
        out = out + residual
        return self.relu(out)


class RedSEResNetAjedrez(nn.Module):
    """Arquitectura SE-ResNet avanzada para ajedrez (v4).

    Integra N bloques residuales con atención por canales Squeeze-and-Excitation,
    permitiendo a la red emular la atención selectiva de un Gran Maestro humano.
    """

    def __init__(
        self,
        canales: int = 128,
        cantidad_bloques: int = 6,
        cantidad_clases: int = NUM_CLASES,
    ):
        super().__init__()
        self.canales = canales
        self.cantidad_bloques = cantidad_bloques
        self.entrada = nn.Sequential(
            nn.Conv2d(12, canales, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(canales),
            nn.ReLU(inplace=True),
        )
        self.torre_residual = nn.Sequential(
            *[BloqueResidualSE(canales) for _ in range(cantidad_bloques)]
        )
        self.cabeza_politica = nn.Sequential(
            nn.Conv2d(canales, 32, kernel_size=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(32 * 8 * 8, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, cantidad_clases),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.entrada(x)
        x = self.torre_residual(x)
        return self.cabeza_politica(x)


