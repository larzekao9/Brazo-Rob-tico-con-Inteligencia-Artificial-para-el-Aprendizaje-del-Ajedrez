"""Esquemas de salida para GET /partida/{id}/analisis-red (análisis jugada por jugada con la red)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CandidataRedResponse(BaseModel):
    jugada: str
    probabilidad: float


class JugadaRedResponse(BaseModel):
    numero: int
    color: str
    quien: str
    fen_antes: str
    jugada: str
    # La jugada que se jugó de verdad, en notación UCI ("e2e4"), para dibujarla en el tablero.
    jugada_uci: str = ""
    red_elige: str | None
    probabilidad_red: float | None
    probabilidad_jugada: float | None
    coincide: bool
    candidatas: list[CandidataRedResponse] = Field(default_factory=list)


class ResumenBloqueRed(BaseModel):
    total: int
    coinciden: int
    porcentaje: float | None


class ResumenRedResponse(BaseModel):
    total_jugadas: int
    coinciden: int
    porcentaje: float | None
    jugador: ResumenBloqueRed
    contraparte: ResumenBloqueRed


class AnalisisRedResponse(BaseModel):
    partida_id: str
    jugadas: list[JugadaRedResponse] = Field(default_factory=list)
    resumen: ResumenRedResponse
