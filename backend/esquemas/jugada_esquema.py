"""Esquemas Pydantic para los endpoints del motor de ajedrez (/jugada, /analisis)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.servicios.motor.motor_ajedrez import NIVEL_MAX, NIVEL_MIN


class JugadaRequest(BaseModel):
    """Cuerpo de entrada para /jugada y /analisis."""

    fen: str
    nivel: int = Field(default=NIVEL_MAX, ge=NIVEL_MIN, le=NIVEL_MAX)


class JugadaResponse(BaseModel):
    """Cuerpo de salida para /jugada."""

    jugada: str


class VarianteCandidata(BaseModel):
    """Una jugada candidata dentro de `variantes_candidatas` (RF21)."""

    jugada: str
    evaluacion_cp: int | None
    mate_en: int | None


class AnalisisResponse(BaseModel):
    """Cuerpo de salida para /analisis."""

    jugada: str | None
    evaluacion_cp: int | None
    mate_en: int | None
    profundidad: int | None = None
    nodos: int | None = None
    variacion_principal: list[str] = Field(default_factory=list)
    variantes_candidatas: list[VarianteCandidata] = Field(default_factory=list)
