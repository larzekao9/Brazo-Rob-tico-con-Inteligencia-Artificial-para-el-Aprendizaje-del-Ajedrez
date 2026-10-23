"""Esquemas Pydantic de las medallas (figuritas)."""
from __future__ import annotations

from pydantic import BaseModel, Field


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


class ReglaMedallaResponse(BaseModel):
    """Una regla elegible. `tipo`: `contador` (con `minimo`, `maximo` y `unidad`), `si_no` o `manual`."""

    codigo: str
    nombre: str
    tipo: str
    minimo: int | None = None
    maximo: int | None = None
    unidad: str | None = None


class PlantillaMedallaResponse(BaseModel):
    nombre: str
    descripcion: str
    nivel: str
    pieza: str
    regla: str
    meta: int


class OpcionesMedallaResponse(BaseModel):
    """Todo lo que necesita la pantalla de creación: reglas, niveles, piezas, ideas listas y largos permitidos."""

    reglas: list[ReglaMedallaResponse]
    niveles: list[str]
    piezas: list[str]
    plantillas: list[PlantillaMedallaResponse]
    largo_nombre: list[int]
    largo_descripcion: list[int]


class CrearMedallaRequest(BaseModel):
    """Cuerpo de POST /medallas. `general` solo lo puede pedir un facilitador principal."""

    nombre: str = Field(min_length=1, max_length=60)
    descripcion: str = Field(min_length=1, max_length=200)
    nivel: str
    pieza: str = "peon"
    regla: str
    meta: int = 1
    general: bool = False


class EditarMedallaRequest(BaseModel):
    """Cuerpo de PATCH /medallas/{codigo}: edición parcial."""

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    descripcion: str | None = Field(default=None, min_length=1, max_length=200)
    nivel: str | None = None
    pieza: str | None = None
    regla: str | None = None
    meta: int | None = None


class MedallaPropiaResponse(BaseModel):
    """Una medalla creada por un facilitador. `imagen_url` es nula mientras no tenga ilustración propia."""

    codigo: str
    nombre: str
    descripcion: str
    nivel: str
    pieza: str
    regla: str
    regla_nombre: str
    meta: int
    general: bool
    creada_por: int
    creador_nombre: str
    es_mia: bool
    ganada_por: int
    imagen_url: str | None = None


class OtorgarMedallaRequest(BaseModel):
    """A quién se entrega una medalla manual: jugadores concretos y/o todos los de un curso."""

    usuario_ids: list[int] = []
    curso_id: int | None = None


class OtorgarMedallaResponse(BaseModel):
    otorgadas: int
    ya_la_tenian: int
