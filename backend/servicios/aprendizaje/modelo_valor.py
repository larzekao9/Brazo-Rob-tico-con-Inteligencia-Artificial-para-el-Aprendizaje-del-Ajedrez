"""Red de valor de Turing: dice QUIÉN VA GANANDO en una posición (la red de política dice qué jugada prefiere).

Misma entrada que la red de política (tensor 12x8x8 visto desde quien mueve) y una sola salida en [-1, 1]:
+1 = gana quien mueve, 0 = igualdad, -1 = pierde quien mueve. Se entrena con evaluaciones de un motor fuerte
(`training/datos_valor.py`) y sirve para reemplazar la evaluación manual de material y posición en la búsqueda
(`busqueda_turing.py`). Es una red aparte y más chica que la de política, para poder evaluar posiciones rápido en CPU.
"""
from __future__ import annotations

from pathlib import Path

import chess
import chess.polyglot
import torch
import torch.nn as nn

from backend.servicios.aprendizaje.modelo_jugadas import BloqueResidualSE
from training.data_pipeline import board_to_tensor
from training.datos_valor import cp_desde_valor


class RedValor(nn.Module):
    """SE-ResNet chica con cabeza escalar `tanh`.

    Args:
        canales: ancho de la torre residual (64 es rápida en CPU; 128 es más precisa y más lenta).
        bloques: cantidad de bloques residuales con atención por canales.
    """

    def __init__(self, canales: int = 64, bloques: int = 4):
        super().__init__()
        self.canales, self.bloques = canales, bloques
        self.entrada = nn.Sequential(
            nn.Conv2d(12, canales, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(canales),
            nn.ReLU(inplace=True),
        )
        self.torre = nn.Sequential(*[BloqueResidualSE(canales) for _ in range(bloques)])
        self.cabeza = nn.Sequential(
            nn.Conv2d(canales, 8, kernel_size=1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(8 * 8 * 8, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """`x` es (N, 12, 8, 8); devuelve (N,) con el valor de cada posición."""
        return self.cabeza(self.torre(self.entrada(x))).squeeze(-1)


class EvaluadorRedValor:
    """Evalúa posiciones con la red de valor, en centipeones desde quien mueve (lo que espera `busqueda_turing.buscar`).

    Guarda en memoria las posiciones ya evaluadas (la búsqueda repite muchas) para no pasar dos veces por la red.
    """

    def __init__(self, ruta_checkpoint: str | Path, maximo_en_memoria: int = 200_000):
        punto = torch.load(ruta_checkpoint, map_location="cpu")
        self.red = RedValor(punto["canales"], punto["bloques"])
        self.red.load_state_dict(punto["state_dict"])
        self.red.eval()
        self._memoria: dict[int, int] = {}
        self._maximo = maximo_en_memoria

    def __call__(self, tablero: chess.Board) -> int:
        clave = chess.polyglot.zobrist_hash(tablero)
        if clave in self._memoria:
            return self._memoria[clave]
        entrada = torch.from_numpy(board_to_tensor(tablero)).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            valor = float(self.red(entrada)[0])
        centipeones = round(cp_desde_valor(valor))
        if len(self._memoria) >= self._maximo:
            self._memoria.clear()
        self._memoria[clave] = centipeones
        return centipeones
