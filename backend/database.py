"""Conexión a la base de datos (PostgreSQL) — sección 7 de PLAN_IMPLEMENTACION_COMPLETO.md.

`DATABASE_URL` se lee de una variable de entorno para no hardcodear ninguna
credencial en el repositorio (ver regla de CLAUDE.md sobre no commitear
secretos). Si no está seteada, el backend sigue funcionando igual que hasta
ahora — en memoria, vía `RepositorioPartidasEnMemoria` — porque no todas las
máquinas del equipo tienen Postgres corriendo (ver `backend/repositorios/repositorio_partida.py::crear_repositorio_partidas`).

Ejemplo de valor para `DATABASE_URL`:
`postgresql+psycopg2://usuario:password@localhost:5432/ajedrez`
"""
from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")


class Base(DeclarativeBase):
    """Clase base declarativa de la que heredan las tablas en `backend/modelos/tablas_orm.py`."""


def obtener_engine() -> Engine:
    """Crea el engine de SQLAlchemy a partir de `DATABASE_URL`.

    Raises:
        RuntimeError: si `DATABASE_URL` no está seteada — se llama solo desde
            código que ya decidió usar Postgres (ver `crear_repositorio_partidas`).
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL no está seteada — no se puede conectar a Postgres. "
            "Setearla como variable de entorno (ver docstring de este módulo) "
            "o seguir usando el repositorio en memoria."
        )
    return create_engine(DATABASE_URL)


def crear_tablas(engine: Engine) -> None:
    """Crea las 4 tablas mínimas (sección 7) si todavía no existen. Idempotente."""
    Base.metadata.create_all(engine)


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Fábrica de sesiones de SQLAlchemy para el engine dado."""
    return sessionmaker(bind=engine)
