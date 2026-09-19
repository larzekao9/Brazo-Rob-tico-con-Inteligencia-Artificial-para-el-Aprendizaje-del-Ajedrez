"""Esquemas Pydantic para los endpoints de partidas jugables (/partida)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.esquemas.jugada_esquema import VarianteCandidata
from backend.servicios.motor.motor_ajedrez import NIVEL_MAX, NIVEL_MIN


class CrearPartidaRequest(BaseModel):
    """Cuerpo de entrada para POST /partida.

    `tipo_oponente` admite `"motor"` (Stockfish) o `"modelo"` (modelo
    propio, HU4) — pedir cualquier otro valor devuelve 400 (ver
    `fabrica_estrategias.TIPOS_SOPORTADOS`).

    `fen_inicial` es opcional: si se manda, la partida arranca en esa
    posición en vez de la inicial estándar — es lo que usa el botón "Usar
    esta posición" tras escanear un tablero físico (`POST /vision/reconocer`).
    """

    nivel: int = Field(default=NIVEL_MAX, ge=NIVEL_MIN, le=NIVEL_MAX)
    tipo_oponente: str = "motor"
    fen_inicial: str | None = None


class EstadoPartidaResponse(BaseModel):
    """Estado completo de una partida, incluidas todas sus jugadas hasta ahora."""

    id: str
    tipo: str
    tipo_oponente: str
    nivel: int
    creada_en: str
    fen: str
    fen_inicial: str
    terminada: bool
    resultado: str | None = None
    jugadas: list[str] = Field(default_factory=list)


class ResumenPartidaResponse(BaseModel):
    """Una fila del registro de partidas — sin la lista completa de jugadas."""

    id: str
    tipo: str
    tipo_oponente: str
    nivel: int
    creada_en: str
    fen: str
    terminada: bool
    resultado: str | None = None
    cantidad_jugadas: int


class MoverRequest(BaseModel):
    """Cuerpo de entrada para POST /partida/{id}/mover. Jugada en notación UCI (ej. "e2e4")."""

    jugada: str


class ResultadoMovimientoResponse(BaseModel):
    """Cuerpo de salida tras aplicar la jugada humana y la respuesta de Stockfish.

    `variantes_candidatas` permite al frontend (HU6) pintar la barra Win% y el
    indicador de calidad de la jugada en tiempo real, sin tener que llamar a
    `/analisis` por separado tras cada movimiento.
    """

    fen: str
    jugada_motor: str | None
    terminada: bool
    resultado: str | None
    jugadas: list[str] = Field(default_factory=list)
    variantes_candidatas: list[VarianteCandidata] = Field(default_factory=list)


class JugadasLegalesResponse(BaseModel):
    """Cuerpo de salida para GET /partida/{id}/jugadas-legales."""

    casillas: list[str] = Field(default_factory=list)


class JugadaAnalisisResponse(BaseModel):
    """El análisis de Stockfish de una jugada ya jugada, para la vista de aprendizaje.

    `evaluacion_cp`/`mate_en` son lo que valió la jugada REALMENTE jugada,
    ya reexpresado en la perspectiva de quien la jugó. `mejor_jugada_motor`,
    `evaluacion_mejor_cp` y `mate_en_mejor` son lo que Stockfish hubiera
    jugado en esa misma posición, en la misma perspectiva — comparar ambos
    pares es lo que permite clasificar la jugada como buena/inexactitud/error/blunder.
    """

    numero_ply: int
    color: str
    jugada_san: str
    fen_antes: str
    fen_despues: str
    evaluacion_cp: int | None
    mate_en: int | None
    mejor_jugada_motor: str | None
    evaluacion_mejor_cp: int | None
    mate_en_mejor: int | None
    variantes_candidatas: list[VarianteCandidata] = Field(default_factory=list)


class AnalisisCompletoResponse(BaseModel):
    """Cuerpo de salida para GET /partida/{id}/analisis-completo."""

    partida_id: str
    jugadas: list[JugadaAnalisisResponse] = Field(default_factory=list)
