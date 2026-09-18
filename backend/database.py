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

from sqlalchemy import Engine, create_engine, inspect, text
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
    """Crea las tablas (sección 7 + `usuario`) si todavía no existen. Idempotente.

    `create_all` no agrega columnas a tablas que ya existían, así que acá se
    aplican a mano las columnas sumadas después de la primera versión de cada
    tabla — hoy solo `usuario.rol` — para que una base local creada antes
    siga funcionando sin tener que borrarla.
    """
    Base.metadata.create_all(engine)
    _agregar_columnas_faltantes(engine)


_COLUMNAS_AGREGADAS: dict[str, dict[str, str]] = {
    "usuario": {"rol": "VARCHAR NOT NULL DEFAULT 'jugador'"},
}


def _agregar_columnas_faltantes(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as conexion:
        for tabla, columnas in _COLUMNAS_AGREGADAS.items():
            if not inspector.has_table(tabla):
                continue
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            for columna, definicion in columnas.items():
                if columna not in existentes:
                    conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"))


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Fábrica de sesiones de SQLAlchemy para el engine dado."""
    return sessionmaker(bind=engine)
