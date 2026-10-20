"""Esquemas Pydantic del endpoint de estado del brazo (/brazo)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EstadoBrazoResponse(BaseModel):
    """Estado del brazo para la pestaña Brazo del front.

    `conectado` es `None` en modo `simulado` (no hay conexión que reportar); en `real` es `True` si el backend ya tiene un
    ejecutor conectado. `ultima_jugada` es la última jugada UCI que el brazo ejecutó sin error.
    """

    modo: Literal["simulado", "real"]
    host: str | None = None
    conectado: bool | None = None
    ultima_jugada: str | None = None
