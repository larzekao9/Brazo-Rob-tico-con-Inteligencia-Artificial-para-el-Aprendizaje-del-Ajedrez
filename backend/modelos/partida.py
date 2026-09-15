"""Entidad de dominio: una partida de ajedrez en curso contra Stockfish."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import chess


@dataclass
class Partida:
    """Una partida en curso. El humano juega blancas.

    `tipo_oponente` selecciona qué `EstrategiaJugada` responde las jugadas del
    humano (HU10, ver PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.1) — hoy solo
    `"motor"` (Stockfish) está implementado.

    `tipo` distingue si el humano jugó tocando el tablero físico (detectado
    por visión, HU1/HU9) o directamente en la interfaz digital — hoy siempre
    es "digital", porque el flujo que usa la cámara para jugar todavía no
    está armado (ver PLAN_IMPLEMENTACION_COMPLETO.md, Módulo 6).

    `fen_inicial` es la posición desde la que arrancó la partida — casi
    siempre la inicial estándar, pero puede ser otra cuando la partida se
    crea a partir de un tablero físico escaneado por visión (`POST /partida`
    con `fen_inicial`, ver `ruta_partida.py`). `jugadas_san` necesita esto
    para reproducir las jugadas desde el punto de partida correcto, no
    siempre desde la posición inicial estándar.
    """

    tablero: chess.Board = field(default_factory=chess.Board)
    nivel: int = 20
    tipo_oponente: str = "motor"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tipo: str = "digital"
    creada_en: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fen_inicial: str = field(default=chess.STARTING_FEN)

    @property
    def fen(self) -> str:
        return self.tablero.fen()

    @property
    def terminada(self) -> bool:
        return self.tablero.is_game_over()

    @property
    def resultado(self) -> str | None:
        return self.tablero.result() if self.terminada else None

    @property
    def jugadas_san(self) -> list[str]:
        """Reconstruye en notación SAN cada jugada jugada hasta ahora, en orden."""
        tablero_reproduccion = chess.Board(self.fen_inicial)
        jugadas = []
        for jugada in self.tablero.move_stack:
            jugadas.append(tablero_reproduccion.san(jugada))
            tablero_reproduccion.push(jugada)
        return jugadas
