"""Patrón Repository: desacopla el guardado del historial de conversación con
el tutor "Turing" (`backend/servicios/tutor/servicio_tutor.py`) de dónde vive
ese historial — mismo patrón exacto que `repositorio_partida.py`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database import fecha_a_iso
from backend.modelos.tablas_orm import MensajeTutorORM


class RepositorioTutor(ABC):
    """Interfaz común para guardar y consultar el historial de turnos con Turing."""

    @abstractmethod
    def agregar_turno(self, usuario_id: int, rol: str, contenido: str) -> None:
        """Persiste un turno de la conversación (`rol` es `'user'` o `'assistant'`)."""

    @abstractmethod
    def obtener_historial(self, usuario_id: int, limite: int = 50) -> list[dict]:
        """Últimos `limite` turnos del usuario, del más viejo al más nuevo.

        Cada elemento es `{"rol": ..., "contenido": ..., "creado_en": ...}`.
        """

    @abstractmethod
    def borrar_historial(self, usuario_id: int) -> None:
        """Borra todo el historial de conversación de un usuario (reset de charla)."""


class RepositorioTutorEnMemoria(RepositorioTutor):
    """Guarda el historial en un dict del proceso — se pierde al reiniciar,
    mismo criterio ya documentado en `RepositorioPartidasEnMemoria`."""

    def __init__(self) -> None:
        self._turnos: dict[int, list[dict]] = {}

    def agregar_turno(self, usuario_id: int, rol: str, contenido: str) -> None:
        self._turnos.setdefault(usuario_id, []).append(
            {
                "rol": rol,
                "contenido": contenido,
                "creado_en": datetime.now(timezone.utc).isoformat(),
            }
        )

    def obtener_historial(self, usuario_id: int, limite: int = 50) -> list[dict]:
        turnos = self._turnos.get(usuario_id, [])
        return turnos[-limite:] if limite else list(turnos)

    def borrar_historial(self, usuario_id: int) -> None:
        self._turnos.pop(usuario_id, None)


class RepositorioTutorPostgres(RepositorioTutor):
    """Guarda el historial en la tabla `mensaje_tutor` (`MensajeTutorORM`) vía SQLAlchemy."""

    def __init__(self, fabrica_sesiones: sessionmaker[Session]) -> None:
        self._fabrica_sesiones = fabrica_sesiones

    def agregar_turno(self, usuario_id: int, rol: str, contenido: str) -> None:
        with self._fabrica_sesiones() as sesion:
            sesion.add(MensajeTutorORM(usuario_id=usuario_id, rol=rol, contenido=contenido))
            sesion.commit()

    def obtener_historial(self, usuario_id: int, limite: int = 50) -> list[dict]:
        with self._fabrica_sesiones() as sesion:
            filas = sesion.scalars(
                select(MensajeTutorORM)
                .where(MensajeTutorORM.usuario_id == usuario_id)
                .order_by(MensajeTutorORM.id.desc())
                .limit(limite)
            ).all()
            return [
                {
                    "rol": fila.rol,
                    "contenido": fila.contenido,
                    "creado_en": fecha_a_iso(fila.creado_en)
                    if hasattr(fila.creado_en, "isoformat")
                    else str(fila.creado_en),
                }
                for fila in reversed(filas)
            ]

    def borrar_historial(self, usuario_id: int) -> None:
        with self._fabrica_sesiones() as sesion:
            sesion.execute(delete(MensajeTutorORM).where(MensajeTutorORM.usuario_id == usuario_id))
            sesion.commit()


def crear_repositorio_tutor() -> RepositorioTutor:
    """Elige la implementación del Repository según si hay Postgres configurado
    — mismo chequeo de `DATABASE_URL` que `crear_repositorio_partidas`."""
    import os

    from backend.database import crear_fabrica_sesiones, crear_tablas, obtener_engine

    if not os.environ.get("DATABASE_URL"):
        return RepositorioTutorEnMemoria()
    engine = obtener_engine()
    crear_tablas(engine)
    return RepositorioTutorPostgres(crear_fabrica_sesiones(engine))
