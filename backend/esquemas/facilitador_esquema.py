"""Esquemas Pydantic del panel de configuración del facilitador."""
from __future__ import annotations

from pydantic import BaseModel


class VideoSubidoResponse(BaseModel):
    """Respuesta de POST /facilitador/videos/{tipo_pieza}."""

    tipo_pieza: str
    url: str
