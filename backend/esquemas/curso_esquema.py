"""Esquemas Pydantic de los cursos (facilitador) y de la inscripción del jugador."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.esquemas.medallas_esquema import ResumenMedallasResponse

TonoCurso = Literal["infantil", "estandar", "adultos", "facilitador"]
"""`facilitador` = el curso usa el tono que el facilitador eligió en su perfil."""


class CrearCursoRequest(BaseModel):
    """Cuerpo de POST /cursos. `facilitador_id` solo lo puede mandar un facilitador principal, para crear el curso
    a nombre de otro facilitador; si no viene, el curso es de quien lo crea."""

    nombre: str = Field(min_length=2, max_length=80)
    cupo: int = Field(default=60, ge=1, le=120)
    preset_ensenanza: TonoCurso | None = None
    facilitador_id: int | None = None


class EditarCursoRequest(BaseModel):
    """Cuerpo de PATCH /cursos/{id}: edición parcial, solo cambia lo que venga.

    `acepta_ingresos=false` cierra el curso: el código deja de servir hasta que se vuelva a abrir.
    `facilitador_id` pasa el curso a otro facilitador activo; solo lo puede hacer un facilitador principal.
    """

    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    acepta_ingresos: bool | None = None
    cupo: int | None = Field(default=None, ge=1, le=120)
    preset_ensenanza: TonoCurso | None = None
    facilitador_id: int | None = None


class CursoResponse(BaseModel):
    """Un curso visto por su facilitador. `codigo` es el que se le da a la clase (con guion, ej. `K7Q-M4T`)."""

    id: int
    nombre: str
    codigo: str
    acepta_ingresos: bool
    cupo: int
    preset_ensenanza: str | None = None
    preset_efectivo: str | None = None
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


class FilaRankingResponse(BaseModel):
    """Una fila del ranking: el nombre es el público (`Ana P.`), nunca el correo ni el apellido completo.

    `medallas` trae cuántas medallas tiene el jugador y las mejores, para mostrarlas junto al nombre.
    """

    puesto: int
    nombre: str
    nivel: int
    rango: str | None = None
    confirmado: bool
    partidas_calibradas: int
    soy_yo: bool
    medallas: ResumenMedallasResponse = ResumenMedallasResponse()


class RankingResponse(BaseModel):
    """Ranking por nivel. `alcance` es `curso` (el curso del jugador) o `general` (los jugadores sin curso).

    `mi_puesto` trae la fila propia solo cuando quedó fuera de los primeros `jugadores`.
    """

    alcance: str
    curso: str | None = None
    total: int
    jugadores: list[FilaRankingResponse]
    mi_puesto: FilaRankingResponse | None = None


class AlumnoReporteResponse(BaseModel):
    """Un alumno en el reporte del curso (el facilitador ve el nombre completo)."""

    id: int
    nombre: str
    activo: bool
    nivel: int | None = None
    rango: str | None = None
    puesto: int | None = None
    confirmado: bool
    precision: float | None = None
    partidas: int
    partidas_7_dias: int
    ultima_partida: str | None = None


class ResumenReporteResponse(BaseModel):
    """Indicadores del curso: participación, práctica y aprendizaje (precisión primera semana vs última)."""

    alumnos_activos_7_dias: int
    porcentaje_activos: float | None = None
    partidas_7_dias: int
    partidas_por_alumno_semana: float | None = None
    precision_primera_semana: float | None = None
    precision_ultima_semana: float | None = None
    variacion_precision: float | None = None


class DatosCursoReporteResponse(BaseModel):
    id: int
    nombre: str
    cupo: int
    alumnos: int


class ReporteCursoResponse(BaseModel):
    """Reporte de un curso para su facilitador."""

    curso: DatosCursoReporteResponse
    resumen: ResumenReporteResponse
    alumnos: list[AlumnoReporteResponse]
