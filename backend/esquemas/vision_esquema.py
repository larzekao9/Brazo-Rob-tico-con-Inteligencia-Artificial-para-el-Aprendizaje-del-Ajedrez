"""Esquemas Pydantic para los endpoints de visión (/vision)."""
from __future__ import annotations

from pydantic import BaseModel


class ReconocerTableroRequest(BaseModel):
    """Cuerpo de entrada para POST /vision/reconocer."""

    turno: str = "w"


class ReconocerTableroResponse(BaseModel):
    """Cuerpo de salida para POST /vision/reconocer."""

    fen: str
