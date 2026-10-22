"""Clasificador de OCUPACIÓN de una casilla: vacía, pieza blanca o pieza negra (sin decir de qué tipo).

Es un problema mucho más fácil que reconocer las 13 clases (el color de las piezas se distingue bien y no depende de la silueta), y
alcanza para detectar jugadas: la app ya sabe la posición, solo necesita ver qué casillas cambiaron de vacía/blanca/negra.
Hay dos formas de recortar cada casilla, y el modelo guarda con cuál se entrenó:

- `"centro"`: el 70 % central del recorte justo de la casilla (lo de siempre).
- `"base"`: la HUELLA de la casilla (`geometria3d.recortes_base`), proyectada con el lente y la posición de la cámara. La base apoya en la
  mesa y por eso queda en su casilla aunque la cabeza de una pieza alta se incline sobre la vecina: así una casilla vacía no se confunde
  con la cabeza de la pieza de al lado.
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
_recorte = "centro"


def clase_a_ocupacion(clase: str) -> str:
    """De las 13 clases del dataset ("white-pawn", "vacia"…) a vacia/blanca/negra."""
    if clase == "vacia":
        return "vacia"
    return "blanca" if clase.startswith("white") else "negra"


def recorte_centro(recorte: np.ndarray, fraccion: float = FRACCION_CENTRO) -> np.ndarray:
    alto, ancho = recorte.shape[:2]
    dy, dx = int(alto * (1 - fraccion) / 2), int(ancho * (1 - fraccion) / 2)
    return recorte[dy : alto - dy, dx : ancho - dx]


def tensor_de_recorte(recorte: np.ndarray, modo: str = "centro") -> torch.Tensor:
    """Tensor para la red: con `"centro"` se toma el 70 % central; con `"base"` el recorte ya es la huella y se usa entero."""
    return preprocesar_recorte(recorte if modo == "base" else recorte_centro(recorte))


def invalidar_modelo() -> None:
    global _modelo
    _modelo = None


def modo_recorte() -> str:
    """Con qué recorte se entrenó el modelo cargado: `"centro"` o `"base"`."""
    _cargar()
    return _recorte


def _cargar() -> RedClasificadoraPiezas:
    global _modelo, _recorte
    if _modelo is None:
        if not RUTA_CHECKPOINT.exists():
            raise FileNotFoundError(
                f"No se encontró {RUTA_CHECKPOINT} — correr antes `python -m training.entrenar_ocupacion`"
            )
        punto = torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)
        modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES_OCUPACION))
        modelo.load_state_dict(punto["pesos"])
        modelo.eval()
        _recorte = punto.get("recorte", "centro")
        _modelo = modelo
    return _modelo


def clasificar_ocupacion(recortes: list[np.ndarray]) -> np.ndarray:
    """Probabilidades `(n, 3)` en el orden de `CLASES_OCUPACION`, una pasada por la red."""
    modelo = _cargar()
    with torch.no_grad():
        return torch.softmax(modelo(torch.stack([tensor_de_recorte(r, _recorte) for r in recortes])), dim=1).numpy()
