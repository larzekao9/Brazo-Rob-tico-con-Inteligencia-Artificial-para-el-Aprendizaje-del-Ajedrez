"""Clasificador de OCUPACIÓN de una casilla: vacía, pieza blanca o pieza negra (sin decir de qué tipo).

Es un problema mucho más fácil que reconocer las 13 clases (el color de las piezas se distingue bien y no depende de la silueta), y
alcanza para detectar jugadas: la app ya sabe la posición, solo necesita ver qué casillas cambiaron de vacía/blanca/negra.
Se mira el CENTRO de la casilla (donde está la base de la pieza), porque las piezas altas se inclinan hacia las vecinas por la
perspectiva de la cámara y ensucian los bordes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from backend.servicios.vision.modelo_piezas import RedClasificadoraPiezas, preprocesar_recorte

CLASES_OCUPACION = ["vacia", "blanca", "negra"]
RUTA_CHECKPOINT = Path("training/checkpoints/clasificador_ocupacion.pt")
FRACCION_CENTRO = 0.7

_modelo: RedClasificadoraPiezas | None = None


def clase_a_ocupacion(clase: str) -> str:
    """De las 13 clases del dataset ("white-pawn", "vacia"…) a vacia/blanca/negra."""
    if clase == "vacia":
        return "vacia"
    return "blanca" if clase.startswith("white") else "negra"


def recorte_centro(recorte: np.ndarray, fraccion: float = FRACCION_CENTRO) -> np.ndarray:
    alto, ancho = recorte.shape[:2]
    dy, dx = int(alto * (1 - fraccion) / 2), int(ancho * (1 - fraccion) / 2)
    return recorte[dy : alto - dy, dx : ancho - dx]


def tensor_de_recorte(recorte: np.ndarray) -> torch.Tensor:
    return preprocesar_recorte(recorte_centro(recorte))


def invalidar_modelo() -> None:
    global _modelo
    _modelo = None


def _cargar() -> RedClasificadoraPiezas:
    global _modelo
    if _modelo is None:
        if not RUTA_CHECKPOINT.exists():
            raise FileNotFoundError(
                f"No se encontró {RUTA_CHECKPOINT} — correr antes `python -m training.entrenar_ocupacion`"
            )
        punto = torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)
        modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES_OCUPACION))
        modelo.load_state_dict(punto["pesos"])
        modelo.eval()
        _modelo = modelo
    return _modelo


def clasificar_ocupacion(recortes: list[np.ndarray]) -> np.ndarray:
    """Probabilidades `(n, 3)` en el orden de `CLASES_OCUPACION`, una pasada por la red."""
    modelo = _cargar()
    with torch.no_grad():
        return torch.softmax(modelo(torch.stack([tensor_de_recorte(r) for r in recortes])), dim=1).numpy()
