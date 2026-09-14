"""Patrón Repository: desacopla el guardado de partidas de la lógica de
`servicio_partida.py` (PLAN_IMPLEMENTACION_COMPLETO.md, sección 4.3).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from datetime import datetime

import chess
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.modelos.partida import Partida
from backend.modelos.tablas_orm import PartidaORM


class RepositorioPartidas(ABC):
    """Interfaz común para guardar y consultar partidas, sin importar dónde vivan."""

    @abstractmethod
    def guardar(self, partida: Partida) -> None:
        """Guarda (o actualiza) una partida."""

    @abstractmethod
    def obtener(self, partida_id: str) -> Partida:
        """Busca una partida por id.

        Raises:
            KeyError: si no existe una partida con ese id.
        """

    @abstractmethod
    def listar(self) -> list[Partida]:
        """Devuelve todas las partidas guardadas, más reciente primero."""


class RepositorioPartidasEnMemoria(RepositorioPartidas):
    """Guarda las partidas en un dict del proceso — se pierden al reiniciar.

    Esto ya es un registro real (todas las partidas que se juegan mientras
    el backend está corriendo quedan acá, consultables), solo que no
    sobrevive un reinicio del servidor. El día que llegue HU11 con
    PostgreSQL (sección 7 del plan), se agrega `RepositorioPartidasPostgres`
    con esta misma interfaz, sin tocar `servicio_partida.py` ni las rutas.
    """

    def __init__(self) -> None:
        self._partidas: dict[str, Partida] = {}

    def guardar(self, partida: Partida) -> None:
        self._partidas[partida.id] = partida

    def obtener(self, partida_id: str) -> Partida:
        if partida_id not in self._partidas:
            raise KeyError(f"No existe una partida con id {partida_id}")
        return self._partidas[partida_id]

    def listar(self) -> list[Partida]:
        return list(reversed(self._partidas.values()))


def _partida_a_fila(partida: Partida) -> PartidaORM:
    """Traduce el dataclass de dominio a la fila de la tabla `partida`."""
    return PartidaORM(
        id=partida.id,
        fecha=datetime.fromisoformat(partida.creada_en),
        resultado=partida.resultado,
        tipo=partida.tipo,
        fen=partida.fen,
        nivel=partida.nivel,
        tipo_oponente=partida.tipo_oponente,
        jugadas_uci=" ".join(jugada.uci() for jugada in partida.tablero.move_stack),
    )


def _fila_a_partida(fila: PartidaORM) -> Partida:
    """Reconstruye el dataclass de dominio desde la fila — recrea el `chess.Board`
    jugada por jugada (no solo el FEN final) para que `jugadas_san` siga funcionando."""
    tablero = chess.Board()
    for jugada_uci in fila.jugadas_uci.split():
        tablero.push_uci(jugada_uci)
    return Partida(
        tablero=tablero,
        nivel=fila.nivel,
        tipo_oponente=fila.tipo_oponente,
        id=fila.id,
        tipo=fila.tipo,
        creada_en=fila.fecha.isoformat() if hasattr(fila.fecha, "isoformat") else str(fila.fecha),
    )


class RepositorioPartidasPostgres(RepositorioPartidas):
    """Guarda las partidas en la tabla `partida` (sección 7 del plan) vía SQLAlchemy.

    Todavía no popula la tabla `jugada` (RF34/HU4 — falta decidir ahí quién
    jugó cada movimiento y con qué tiempo de cálculo); esta implementación
    solo cubre lo que la interfaz `RepositorioPartidas` ya necesita hoy.
    """

    def __init__(self, fabrica_sesiones: sessionmaker[Session]) -> None:
        self._fabrica_sesiones = fabrica_sesiones

    def guardar(self, partida: Partida) -> None:
        with self._fabrica_sesiones() as sesion:
            fila_existente = sesion.get(PartidaORM, partida.id)
            fila_nueva = _partida_a_fila(partida)
            if fila_existente is None:
                sesion.add(fila_nueva)
            else:
                for columna in ("resultado", "fen", "nivel", "tipo_oponente", "jugadas_uci"):
                    setattr(fila_existente, columna, getattr(fila_nueva, columna))
            sesion.commit()

    def obtener(self, partida_id: str) -> Partida:
        with self._fabrica_sesiones() as sesion:
            fila = sesion.get(PartidaORM, partida_id)
            if fila is None:
                raise KeyError(f"No existe una partida con id {partida_id}")
            return _fila_a_partida(fila)

    def listar(self) -> list[Partida]:
        with self._fabrica_sesiones() as sesion:
            filas = sesion.scalars(select(PartidaORM).order_by(PartidaORM.fecha.desc())).all()
            return [_fila_a_partida(fila) for fila in filas]


def crear_repositorio_partidas() -> RepositorioPartidas:
    """Elige la implementación del Repository según si hay Postgres configurado.

    Si `DATABASE_URL` está seteada, usa `RepositorioPartidasPostgres` (y crea
    las tablas si todavía no existen). Si no, sigue usando
    `RepositorioPartidasEnMemoria` — así ninguna máquina del equipo necesita
    tener Postgres corriendo solo para levantar el backend.
    """
    from backend.database import DATABASE_URL, crear_fabrica_sesiones, crear_tablas, obtener_engine

    if not DATABASE_URL:
        return RepositorioPartidasEnMemoria()
    engine = obtener_engine()
    crear_tablas(engine)
    return RepositorioPartidasPostgres(crear_fabrica_sesiones(engine))
