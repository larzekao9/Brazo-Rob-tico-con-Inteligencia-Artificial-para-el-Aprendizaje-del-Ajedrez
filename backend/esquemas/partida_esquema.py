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


class RetroalimentacionEnVivo(BaseModel):
    """Retroalimentación pedagógica e indicador de calidad en tiempo real (HU6)."""

    calidad: str = "buena"  # 'brillante', 'mejor', 'excelente', 'buena', 'imprecision', 'error', 'blunder'
    perdida_cp: int = 0
    probabilidad_victoria: float = 50.0  # Win% según fórmula Lichess
    principio_ajedrecistico: str = "general"
    explicacion: str = ""
    mejor_alternativa: str | None = None


class ResultadoMovimientoResponse(BaseModel):
    """Cuerpo de salida tras aplicar la jugada humana y la respuesta de Stockfish.

    `variantes_candidatas` y `retroalimentacion_en_vivo` permiten al frontend y móvil
    (HU6) pintar la barra Win%, el indicador de calidad y el consejo pedagógico en tiempo real.
    """

    fen: str
    jugada_motor: str | None
    terminada: bool
    resultado: str | None
    jugadas: list[str] = Field(default_factory=list)
    variantes_candidatas: list[VarianteCandidata] = Field(default_factory=list)
    retroalimentacion_en_vivo: RetroalimentacionEnVivo | None = None


class JugadasLegalesResponse(BaseModel):
    """Cuerpo de salida para GET /partida/{id}/jugadas-legales."""

    casillas: list[str] = Field(default_factory=list)


class JugadaAnalisisResponse(BaseModel):
    """El análisis de una jugada ya jugada con evaluación y tutoría pedagógica (HU5)."""

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
    calidad: str = "buena"
    perdida_cp: int = 0
    probabilidad_victoria: float = 50.0
    principio_ajedrecistico: str = "general"
    explicacion: str = ""


class ResumenRendimiento(BaseModel):
    """Resumen analítico post-partida, curva de efectividad y consejo del tutor (HU5)."""

    precision_global: float
    conteo_calidad: dict[str, int]
    curva_efectividad: list[dict] = Field(default_factory=list)
    consejo_tutor: str
    total_jugadas: int


class AnalisisCompletoResponse(BaseModel):
    """Cuerpo de salida para GET /partida/{id}/analisis-completo (HU5/HU6)."""

    partida_id: str
    jugadas: list[JugadaAnalisisResponse] = Field(default_factory=list)
    resumen: ResumenRendimiento | None = None
