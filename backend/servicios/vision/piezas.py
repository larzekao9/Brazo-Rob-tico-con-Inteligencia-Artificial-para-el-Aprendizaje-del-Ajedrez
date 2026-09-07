"""Clasifica qué pieza hay en el recorte de una casilla (HU1, segunda etapa).

Carga el checkpoint entrenado por `training/entrenar_clasificador_piezas.py`
una sola vez (perezoso, en el primer llamado) y lo reusa para el resto de la
ejecución del backend.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from backend.servicios.vision.modelo_piezas import RedClasificadoraPiezas, preprocesar_recorte

RUTA_CHECKPOINT = Path("training/checkpoints/clasificador_piezas.pt")

_modelo: RedClasificadoraPiezas | None = None
_clases: list[str] | None = None


def _cargar_modelo() -> tuple[RedClasificadoraPiezas, list[str]]:
    global _modelo, _clases
    if _modelo is None:
        if not RUTA_CHECKPOINT.exists():
            raise FileNotFoundError(
                f"No se encontró {RUTA_CHECKPOINT} — correr antes "
                "`python -m training.entrenar_clasificador_piezas`"
            )
        checkpoint = torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)
        _clases = checkpoint["clases"]
        modelo = RedClasificadoraPiezas(cantidad_clases=len(_clases))
        modelo.load_state_dict(checkpoint["pesos"])
        modelo.eval()
        _modelo = modelo
    return _modelo, _clases


def clasificar_pieza(recorte_casilla: np.ndarray) -> str:
    """Predice qué hay en una casilla: "vacia" o una pieza (ej. "white-knight").

    Args:
        recorte_casilla: recorte BGR de la casilla, tal como lo devuelve
            `backend.servicios.vision.tablero.dividir_en_casillas`.

    Returns:
        La etiqueta de clase con mayor probabilidad.
    """
    modelo, clases = _cargar_modelo()
    entrada = preprocesar_recorte(recorte_casilla).unsqueeze(0)  # agrega dimensión de lote
    with torch.no_grad():
        indice = modelo(entrada).argmax(dim=1).item()
    return clases[indice]
