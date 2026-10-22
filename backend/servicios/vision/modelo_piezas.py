"""Constantes de dominio y arquitectura de la CNN de clasificación de piezas (HU1).

Vive acá (no en `training/`) porque es el contrato del servicio de visión:
tanto `training/dataset_piezas.py` y `training/entrenar_clasificador_piezas.py`
(arman los datos y la entrenan) como `backend/servicios/vision/piezas.py` (la
usa en producción) importan esta misma definición — así ninguno de los dos
depende del otro, ambos dependen de este módulo compartido.
"""
from __future__ import annotations

import cv2
import numpy as np
import torch
from torch import nn

CLASE_VACIA = "vacia"
CATEGORIAS_VALIDAS = {
    "white-pawn", "white-knight", "white-bishop", "white-rook", "white-queen", "white-king",
    "black-pawn", "black-knight", "black-bishop", "black-rook", "black-queen", "black-king",
}
CLASES = sorted(CATEGORIAS_VALIDAS) + [CLASE_VACIA]

TAMANO_ENTRADA = 64  # las casillas se reducen a 64x64 antes de entrar a la red


def preprocesar_recorte(recorte_bgr: np.ndarray, tamano: int = TAMANO_ENTRADA) -> torch.Tensor:
    """Redimensiona y normaliza un recorte de casilla para la red.

    Se comparte entre entrenamiento e inferencia para que ambos lados
    apliquen exactamente el mismo preprocesamiento. `tamano` es el lado de entrada de la red (64 por defecto; el clasificador de
    piezas con recorte ampliado usa 96).
    """
    redimensionado = cv2.resize(recorte_bgr, (tamano, tamano))
    rgb = cv2.cvtColor(redimensionado, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return torch.from_numpy(rgb).permute(2, 0, 1)  # (C, H, W)


class RedClasificadoraPiezas(nn.Module):
    """CNN chica: 3 bloques conv+batchnorm+pool y una cabeza lineal a `len(CLASES)`.

    No busca precisión de investigación, busca ser suficiente para un tablero
    con piezas bien diferenciadas (ver PLAN_IMPLEMENTACION_COMPLETO.md,
    sección 15) y liviana para entrenar sin GPU en el tiempo que queda.
    """

    def __init__(self, cantidad_clases: int = len(CLASES), tamano: int = TAMANO_ENTRADA):
        super().__init__()
        self.caracteristicas = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),   # 64 -> 32
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),  # 32 -> 16
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),  # 16 -> 8
        )
        self.clasificador = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * (tamano // 8) ** 2, 128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, cantidad_clases),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.clasificador(self.caracteristicas(x))


class RedDosVistas(nn.Module):
    """Clasifica una casilla mirando a la vez el recorte de la cámara principal y el de la secundaria.

    Las dos vistas pasan por los mismos bloques convolucionales (mismos pesos) y sus descriptores se concatenan antes de decidir; así la red
    aprende sola a cuál vista creerle según la pieza (una pieza tapada o inclinada en una cámara suele verse bien en la otra). `mascara` es
    `(lote, 2)` con 1 donde hay vista y 0 donde falta: con 0 el descriptor de esa vista se anula, por eso funciona también con una sola
    cámara si se la entrenó quitando vistas al azar.
    """

    def __init__(self, cantidad_clases: int = len(CLASES), tamano: int = TAMANO_ENTRADA):
        super().__init__()
        self.caracteristicas = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.reduccion = nn.Sequential(nn.Flatten(), nn.Linear(64 * (tamano // 8) ** 2, 128), nn.ReLU())
        self.clasificador = nn.Sequential(nn.Dropout(0.3), nn.Linear(256, 128), nn.ReLU(), nn.Linear(128, cantidad_clases))

    def forward(self, principal: torch.Tensor, secundaria: torch.Tensor, mascara: torch.Tensor) -> torch.Tensor:
        a = self.reduccion(self.caracteristicas(principal)) * mascara[:, 0:1]
        b = self.reduccion(self.caracteristicas(secundaria)) * mascara[:, 1:2]
        return self.clasificador(torch.cat([a, b], dim=1))
