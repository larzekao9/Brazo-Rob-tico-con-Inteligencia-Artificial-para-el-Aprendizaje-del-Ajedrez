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
    usuario_id: int | None = None
    """Dueño de la partida (HU10) — quién puede consultarla vía `GET /partida/{id}`.

    `None` para partidas creadas antes de que la autenticación fuera
    obligatoria en `POST /partida`; esas quedan sin dueño y no se bloquean
    por el chequeo de autorización (ver `ruta_partida.py::estado`)."""
    permite_simulacion_3d: bool = False
    permite_camara: bool = False
    """Funciones educativas opcionales que el jugador ve apagadas por defecto
    y el facilitador puede prender por partida (`PATCH /partida/{id}/permisos`,
    solo facilitador — ver `ruta_partida.py`). El E-STOP del brazo no es una de
    estas: es un control de seguridad, se queda hardcodeado solo-facilitador
    sin toggle y no vive en este dataclass."""
    es_demostracion: bool = False
    """Marca la partida que el facilitador está transmitiendo en vivo a toda
    la clase (jugar de ejemplo delante de los jugadores) — se prende con el
    mismo `PATCH /partida/{id}/permisos` que los dos campos de arriba, pero
    solo tiene sentido sobre una partida propia del facilitador (ver
    `servicio_partida.actualizar_permisos`, que valida eso y además apaga
    cualquier otra partida que estuviera en demostración: solo puede haber
    una transmisión activa a la vez en todo el sistema). Mientras está en
    `True`, cualquier jugador autenticado puede leer esta partida vía
    `GET /partida/{id}` sin ser su dueño ni facilitador (ver
    `ruta_partida.py::estado`), y `GET /partida/demostracion-activa` la
    devuelve sin necesidad de conocer su id de antemano."""

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
