"""Esquemas Pydantic de los cursos (facilitador) y de la inscripción del jugador."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CrearCursoRequest(BaseModel):
    """Cuerpo de POST /cursos. `facilitador_id` solo lo puede mandar un facilitador principal, para crear el curso
    a nombre de otro facilitador; si no viene, el curso es de quien lo crea."""

    nombre: str = Field(min_length=2, max_length=80)
    facilitador_id: int | None = None


class EditarCursoRequest(BaseModel):
    """Cuerpo de PATCH /cursos/{id}: edición parcial, solo cambia lo que venga.

    `acepta_ingresos=false` cierra el curso: el código deja de servir hasta que se vuelva a abrir.
    `facilitador_id` pasa el curso a otro facilitador activo; solo lo puede hacer un facilitador principal.
    """

    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    acepta_ingresos: bool | None = None
    facilitador_id: int | None = None


class CursoResponse(BaseModel):
    """Un curso visto por su facilitador. `codigo` es el que se le da a la clase (con guion, ej. `K7Q-M4T`)."""

    id: int
    nombre: str
    codigo: str
    acepta_ingresos: bool
    estudiantes: int
    creado_en: str
    facilitador_id: int
    facilitador_nombre: str


class EstudianteDeCursoResponse(BaseModel):
    """Un jugador inscrito en un curso, para que el facilitador lo siga."""

    id: int
    nombre: str
    email: str
    avatar_url: str | None = None
    nivel_estimado: int | None = None
    rango_estimado: str | None = None
    activo: bool = True
    unido_en: str


class UnirseCursoRequest(BaseModel):
    """Cuerpo de POST /cursos/unirse: el código que le dio el facilitador (acepta mayúsculas, minúsculas y guion)."""

    codigo: str = Field(min_length=1, max_length=20)


class CursoDelJugadorResponse(BaseModel):
    """El curso del jugador visto por él: quién lo enseña y con qué tono le habla Turing."""

    id: int
    nombre: str
    facilitador_nombre: str
    facilitador_avatar_url: str | None = None
    preset_ensenanza: str | None = None
