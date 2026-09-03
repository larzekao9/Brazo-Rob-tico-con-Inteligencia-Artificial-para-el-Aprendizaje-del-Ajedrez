"""Entidad de dominio: una partida de ajedrez en curso contra Stockfish."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import chess


@dataclass
class Partida:
    """Una partida en curso. El humano juega blancas, Stockfish juega negras."""

    tablero: chess.Board = field(default_factory=chess.Board)
    nivel: int = 20
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def fen(self) -> str:
        return self.tablero.fen()

    @property
    def terminada(self) -> bool:
        return self.tablero.is_game_over()

    @property
    def resultado(self) -> str | None:
        return self.tablero.result() if self.terminada else None
