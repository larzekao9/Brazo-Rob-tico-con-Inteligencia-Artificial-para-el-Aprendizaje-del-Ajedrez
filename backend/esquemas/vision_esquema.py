"""Esquemas Pydantic para los endpoints de visión (/vision).

POST /vision/reconocer recibe `turno` y (opcionalmente) `foto_subida` como
multipart/form-data, no JSON — para poder mandar una imagen no hay un
esquema Pydantic de entrada, los parámetros se declaran directo en
`ruta_vision.py` con `Form`/`File`.
"""
from __future__ import annotations

from pydantic import BaseModel


class ReconocerTableroResponse(BaseModel):
    """Cuerpo de salida para POST /vision/reconocer."""

    fen: str
