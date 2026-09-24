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

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

if os.environ.get("PYTEST_RUNNING") != "1":
    load_dotenv()
    DATABASE_URL = os.environ.get("DATABASE_URL")
else:
    DATABASE_URL = None


class Base(DeclarativeBase):
    """Clase base declarativa de la que heredan las tablas en `backend/modelos/tablas_orm.py`."""


def obtener_engine() -> Engine:
    """Crea el engine de SQLAlchemy a partir de `DATABASE_URL` (PostgreSQL o SQLite)."""
    db_url = os.environ.get("DATABASE_URL") or DATABASE_URL or "sqlite:///./ajedrez.db"
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    return create_engine(db_url)


def crear_tablas(engine: Engine) -> None:
    """Crea las tablas (sección 7 + `usuario`) si todavía no existen. Idempotente.

    Aplica columnas faltantes si la base ya existía y siembra los usuarios
    iniciales de prueba para desarrollo y demostración.
    """
    Base.metadata.create_all(engine)
    _agregar_columnas_faltantes(engine)
    sembrar_usuarios_iniciales(engine)


_COLUMNAS_AGREGADAS: dict[str, dict[str, str]] = {
    "usuario": {
        "rol": "VARCHAR NOT NULL DEFAULT 'jugador'",
        "nivel_estimado": "INTEGER",
        "rango_estimado": "VARCHAR",
        "google_id": "VARCHAR",
        "avatar_url": "VARCHAR",
    },
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


def sembrar_usuarios_iniciales(engine: Engine) -> None:
    """Crea los usuarios iniciales (facilitador y jugador) si no existen todavía."""
    from backend.modelos.tablas_orm import UsuarioORM
    from backend.servicios.auth.servicio_auth import hash_password

    fabrica = sessionmaker(bind=engine)
    with fabrica() as session:
        # 1. Facilitador de prueba (clave: admin123)
        facilitador = session.execute(
            select(UsuarioORM).where(UsuarioORM.email == "facilitador@test.com")
        ).scalar_one_or_none()
        if not facilitador:
            session.add(
                UsuarioORM(
                    email="facilitador@test.com",
                    nombre="Facilitador Árbitro",
                    password_hash=hash_password("admin123"),
                    rol="facilitador",
                    activo=True,
                )
            )

        # 2. Jugador de prueba (clave: test123456)
        jugador = session.execute(
            select(UsuarioORM).where(UsuarioORM.email == "jugador@test.com")
        ).scalar_one_or_none()
        if not jugador:
            session.add(
                UsuarioORM(
                    email="jugador@test.com",
                    nombre="Jugador Aspirante",
                    password_hash=hash_password("test123456"),
                    rol="jugador",
                    activo=True,
                )
            )

        # 3. Jugador KAIROS (clave: test123456)
        jugador_kairos = session.execute(
            select(UsuarioORM).where(UsuarioORM.email == "jugador@kairos-chess.ai")
        ).scalar_one_or_none()
        if not jugador_kairos:
            session.add(
                UsuarioORM(
                    email="jugador@kairos-chess.ai",
                    nombre="Jugador Kairos Core",
                    password_hash=hash_password("test123456"),
                    rol="jugador",
                    activo=True,
                )
            )

        # 4. Facilitador Hebert Suarez Burgos
        facilitador_hebert = session.execute(
            select(UsuarioORM).where(UsuarioORM.email == "suarezburgoshebert@gmail.com")
        ).scalar_one_or_none()
        if not facilitador_hebert:
            session.add(
                UsuarioORM(
                    email="suarezburgoshebert@gmail.com",
                    nombre="Hebert Suarez Burgos",
                    password_hash=hash_password("admin123"),
                    rol="facilitador",
                    activo=True,
                )
            )
        elif facilitador_hebert.rol != "facilitador":
            facilitador_hebert.rol = "facilitador"

        session.commit()


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Fábrica de sesiones de SQLAlchemy para el engine dado."""
    return sessionmaker(bind=engine)
