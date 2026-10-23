"""Esquemas Pydantic de las medallas (figuritas)."""
from __future__ import annotations

from pydantic import BaseModel


class MedallaResponse(BaseModel):
    """Una medalla del álbum. `imagen_url` es nula cuando se usa la figurita dibujada de fábrica."""

    codigo: str
    nombre: str
    descripcion: str
    nivel: str
    pieza: str
    meta: int
    progreso: int
    ganada: bool
    ganada_en: str | None = None
    nueva: bool
    imagen_url: str | None = None


class MedallasResponse(BaseModel):
    """El álbum del jugador. `nuevas` son las ganadas que todavía no se le avisaron; `es_primera` indica que entre ellas
    está su primera medalla (celebración grande); las demás se avisan con una notificación arriba."""

    medallas: list[MedallaResponse]
    total: int
    ganadas: int
    nuevas: list[str]
    es_primera: bool


class MarcarVistasRequest(BaseModel):
    """Códigos a marcar como vistos; sin lista (`null`), todos."""

    codigos: list[str] | None = None


class MarcarVistasResponse(BaseModel):
    marcadas: int


class MedallaDestacadaResponse(BaseModel):
    codigo: str
    nombre: str
    nivel: str
    pieza: str
    imagen_url: str | None = None


class ResumenMedallasResponse(BaseModel):
    """Medallas de un jugador para mostrar en el ranking: el total y las mejores."""

    total: int = 0
    destacadas: list[MedallaDestacadaResponse] = []


class ImagenMedallaResponse(BaseModel):
    codigo: str
    imagen_url: str
