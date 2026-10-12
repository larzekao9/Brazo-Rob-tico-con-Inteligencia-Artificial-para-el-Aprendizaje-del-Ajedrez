"""Esquemas Pydantic para los endpoints de salas (humano vs humano)."""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class CrearSalaRequest(BaseModel):
    """Cuerpo de entrada para POST /sala.

    `color` elige qué lado juega el creador: "blancas", "negras" o "aleatorio".
    """

    color: str = Field(default="aleatorio", pattern="^(blancas|negras|aleatorio)$")


class JugadorSalaResponse(BaseModel):
    """Info básica de un jugador en la sala (solo id, nombre, avatar)."""

    id: int
    nombre: str
    avatar_url: Optional[str] = None


class SalaResponse(BaseModel):
    """Estado completo de una sala (partida humano vs humano)."""

    codigo: str
    partida_id: str
    estado: str  # "esperando" | "en_curso" | "terminada" | "abandonada"
    fen: str
    turno: str  # "blancas" | "negras"
    jugadas: list[str] = Field(default_factory=list)
    ultima_jugada_uci: Optional[str] = None
    terminada: bool
    resultado: Optional[str] = None  # "1-0" | "0-1" | "1/2-1/2"
    motivo_fin: Optional[str] = None
    """`"mate"` | `"tablas"` | `"abandono"` | `"inactividad"` | `None` (sala sin terminar).

    - `"abandono"`: un jugador abandonó (`estado == "terminada"`): hay `resultado` y ganador.
    - `"inactividad"`: la sala venció por inactividad (`estado == "abandonada"`, `terminada: true`):
      `resultado` es `null` (nadie ganó); el front la muestra como "partida cancelada por inactividad".
    """
    blancas: Optional[JugadorSalaResponse] = None
    negras: Optional[JugadorSalaResponse] = None
    rol: str  # "blancas" | "negras" | "espectador" (de quien consulta)
    version: int  # cantidad de plies + indicador de estado


class MoverSalaRequest(BaseModel):
    """Cuerpo de entrada para POST /sala/{codigo}/mover. Jugada en notación UCI."""

    jugada: str


class UnirseSalaResponse(BaseModel):
    """Respuesta de POST /sala/{codigo}/unirse."""

    codigo: str
    partida_id: str
    rol: str  # "blancas" | "negras" | "espectador"


class JugadasLegalesSalaResponse(BaseModel):
    """Cuerpo de salida para GET /sala/{codigo}/jugadas-legales."""

    casillas: list[str] = Field(default_factory=list)


class AnalisisSalaResponse(BaseModel):
    """Análisis general con Stockfish de una sala terminada."""

    codigo: str
    resultado: Optional[str] = None  # `null` si la sala venció por inactividad
    motivo_fin: Optional[str] = None  # "mate" | "tablas" | "abandono" | "inactividad"
    total_jugadas: int
    blancas: dict  # nombre, precision (None sin jugadas), mejores, imprecisiones, errores, blunders
    negras: dict
    curva: list[dict]  # ply, evaluacion_cp, mate_en
    momentos_clave: list[dict]  # ply, color, jugada_san, calidad, perdida_cp, mejor_jugada_san, explicacion
    jugadas: list[dict]  # lista completa del análisis


class SalaActivaResponse(BaseModel):
    """Respuesta de GET /sala/activa — la sala más reciente del usuario."""

    codigo: str
    partida_id: str
    estado: str
    fen: str
    turno: str
    jugadas: list[str]
    ultima_jugada_uci: Optional[str]
    terminada: bool
    resultado: Optional[str]
    motivo_fin: Optional[str]
    blancas: Optional[JugadorSalaResponse]
    negras: Optional[JugadorSalaResponse]
    rol: str
    version: int