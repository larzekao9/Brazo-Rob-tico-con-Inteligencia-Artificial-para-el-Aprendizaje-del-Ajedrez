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


def invalidar_modelo() -> None:
    """Descarta el clasificador cacheado: el próximo `clasificar_pieza` recarga el checkpoint (tras un reentrenamiento)."""
    global _modelo, _clases
    _modelo = None
    _clases = None


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


def clasificar_con_confianza(recortes: list[np.ndarray], cantidad: int = 3) -> list[list[tuple[str, float]]]:
    """Para cada recorte, las `cantidad` clases más probables con su probabilidad (una sola pasada por la red)."""
    if not recortes:
        return []
    modelo, clases = _cargar_modelo()
    entradas = torch.stack([preprocesar_recorte(r) for r in recortes])
    with torch.no_grad():
        probabilidades = torch.softmax(modelo(entradas), dim=1)
    mejores = probabilidades.topk(min(cantidad, len(clases)), dim=1)
    return [
        [(clases[i], float(p)) for p, i in zip(fila_p.tolist(), fila_i.tolist())]
        for fila_p, fila_i in zip(mejores.values, mejores.indices)
    ]
