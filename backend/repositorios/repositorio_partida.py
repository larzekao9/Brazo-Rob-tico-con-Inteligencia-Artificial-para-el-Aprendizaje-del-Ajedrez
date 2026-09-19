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
from backend.modelos.tablas_orm import JugadaORM, PartidaORM


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

    @abstractmethod
    def registrar_jugada(
        self, partida_id: str, numero: int, fen_antes: str, movimiento: str, decidido_por: str
    ) -> None:
        """Persiste una fila de la tabla `jugada` (RF34/HU4) por cada movimiento aplicado.

        `movimiento` va en notación UCI; `decidido_por` es `'jugador'`,
        `'motor'` o `'modelo'` según quién decidió esa jugada puntual.
        """

    @abstractmethod
    def actualizar_evaluacion_jugada(
        self,
        partida_id: str,
        numero: int,
        evaluacion_cp: int | None,
        mate_en: int | None,
        evaluacion_mejor_cp: int | None,
        mate_en_mejor: int | None,
    ) -> None:
        """Persiste la evaluación de Stockfish de una jugada ya registrada (HU5/HU14).

        La llama `servicio_partida.analisis_completo()` una vez por jugada,
        aprovechando que ese endpoint ya recalcula con Stockfish la evaluación
        de cada jugada de la partida — así `/usuario/estadisticas` puede armar
        `top_errores` sin volver a llamar a Stockfish. No-op si la fila
        `(partida_id, numero)` no existe todavía (partida jugada antes de que
        existiera esta persistencia, o repo en memoria).
        """


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

    def registrar_jugada(
        self, partida_id: str, numero: int, fen_antes: str, movimiento: str, decidido_por: str
    ) -> None:
        """No-op a propósito: en memoria no existe una tabla `jugada` a la que
        escribir. En la práctica esto solo importa mientras no haya
        `DATABASE_URL` seteada — y sin ella tampoco funciona la autenticación
        (HU10, ver `ruta_auth.get_db`), así que un despliegue real siempre
        termina usando `RepositorioPartidasPostgres` en su lugar."""

    def actualizar_evaluacion_jugada(
        self,
        partida_id: str,
        numero: int,
        evaluacion_cp: int | None,
        mate_en: int | None,
        evaluacion_mejor_cp: int | None,
        mate_en_mejor: int | None,
    ) -> None:
        """No-op por el mismo motivo que `registrar_jugada`: no hay fila de
        `jugada` en memoria a la que actualizarle la evaluación."""


def _partida_a_fila(partida: Partida) -> PartidaORM:
    """Traduce el dataclass de dominio a la fila de la tabla `partida`."""
    return PartidaORM(
        id=partida.id,
        usuario_id=partida.usuario_id,
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
        usuario_id=fila.usuario_id,
    )


class RepositorioPartidasPostgres(RepositorioPartidas):
    """Guarda las partidas en la tabla `partida` (sección 7 del plan) vía SQLAlchemy.

    También popula la tabla `jugada` (RF34/HU4, ver `registrar_jugada`) con
    una fila por movimiento aplicado — quién lo decidió, no todavía tiempo de
    cálculo ni explicación.
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
                for columna in ("usuario_id", "resultado", "fen", "nivel", "tipo_oponente", "jugadas_uci"):
                    setattr(fila_existente, columna, getattr(fila_nueva, columna))
            sesion.commit()

    def registrar_jugada(
        self, partida_id: str, numero: int, fen_antes: str, movimiento: str, decidido_por: str
    ) -> None:
        with self._fabrica_sesiones() as sesion:
            sesion.add(
                JugadaORM(
                    partida_id=partida_id,
                    numero=numero,
                    fen_antes=fen_antes,
                    movimiento=movimiento,
                    decidido_por=decidido_por,
                )
            )
            sesion.commit()

    def obtener(self, partida_id: str) -> Partida:
        with self._fabrica_sesiones() as sesion:
            fila = sesion.get(PartidaORM, partida_id)
            if fila is None:
                raise KeyError(f"No existe una partida con id {partida_id}")
            return _fila_a_partida(fila)

    def actualizar_evaluacion_jugada(
        self,
        partida_id: str,
        numero: int,
        evaluacion_cp: int | None,
        mate_en: int | None,
        evaluacion_mejor_cp: int | None,
        mate_en_mejor: int | None,
    ) -> None:
        with self._fabrica_sesiones() as sesion:
            fila = sesion.scalar(
                select(JugadaORM).where(
                    JugadaORM.partida_id == partida_id, JugadaORM.numero == numero
                )
            )
            if fila is None:
                return
            fila.evaluacion_cp = evaluacion_cp
            fila.mate_en = mate_en
            fila.evaluacion_mejor_cp = evaluacion_mejor_cp
            fila.mate_en_mejor = mate_en_mejor
            sesion.commit()

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
