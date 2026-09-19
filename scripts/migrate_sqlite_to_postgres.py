#!/usr/bin/env python3
"""Script para migrar datos de SQLite (test.db) a PostgreSQL.

Este script lee los datos del archivo test.db (SQLite) y los inserta en la
base de datos PostgreSQL configurada mediante la variable de entorno DATABASE_URL.

Uso:
    DATABASE_URL=postgresql+psycopg2://ajedrez:ajedrez@localhost:5432/ajedrez python scripts/migrate_sqlite_to_postgres.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

# Añadir el directorio raíz al path para importar los modelos del backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.modelos.tablas_orm import (
    Base,
    JugadaORM,
    PartidaORM,
    ParticipanteORM,
    SesionORM,
    UsuarioORM,
)


def get_sqlite_connection():
    """Conecta a la base de datos SQLite test.db."""
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test.db")
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"No se encuentra test.db en {sqlite_path}")
    return sqlite3.connect(sqlite_path)


def get_postgres_engine():
    """Crea el engine de PostgreSQL desde DATABASE_URL."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está seteada. Configúrala como variable de entorno.")
    return create_engine(database_url)


def migrate_usuarios(sqlite_conn: sqlite3.Connection, pg_session: Session) -> dict[int, int]:
    """Migra usuarios de SQLite a PostgreSQL.

    Retorna un mapeo de id_sqlite -> id_postgres para mantener referencias.
    """
    print("Migrando usuarios...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT id, email, nombre, password_hash, creado_en, activo, rol, nivel_estimado, rango_estimado FROM usuario")
    rows = cursor.fetchall()

    id_map = {}
    for row in rows:
        sqlite_id, email, nombre, password_hash, creado_en, activo, rol, nivel_estimado, rango_estimado = row

        # Verificar si ya existe en PostgreSQL (por email)
        existing = pg_session.query(UsuarioORM).filter_by(email=email).first()
        if existing:
            print(f"  Usuario {email} ya existe en PostgreSQL (id={existing.id}), saltando...")
            id_map[sqlite_id] = existing.id
            continue

        usuario = UsuarioORM(
            email=email,
            nombre=nombre,
            password_hash=password_hash,
            creado_en=datetime.fromisoformat(creado_en) if isinstance(creado_en, str) else creado_en,
            activo=bool(activo),
            rol=rol or "jugador",
            nivel_estimado=nivel_estimado,
            rango_estimado=rango_estimado,
        )
        pg_session.add(usuario)
        pg_session.flush()  # Para obtener el ID generado
        id_map[sqlite_id] = usuario.id
        print(f"  Migrado usuario {email} (SQLite id={sqlite_id} -> PG id={usuario.id})")

    pg_session.commit()
    return id_map


def migrate_participantes(sqlite_conn: sqlite3.Connection, pg_session: Session) -> dict[int, int]:
    """Migra participantes de SQLite a PostgreSQL."""
    print("Migrando participantes...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT id, nombre FROM participante")
    rows = cursor.fetchall()

    id_map = {}
    for row in rows:
        sqlite_id, nombre = row

        existing = pg_session.query(ParticipanteORM).filter_by(id=sqlite_id).first()
        if existing:
            print(f"  Participante {nombre} (id={sqlite_id}) ya existe, saltando...")
            id_map[sqlite_id] = existing.id
            continue

        participante = ParticipanteORM(id=sqlite_id, nombre=nombre)
        pg_session.add(participante)
        id_map[sqlite_id] = sqlite_id
        print(f"  Migrado participante {nombre} (id={sqlite_id})")

    pg_session.commit()
    return id_map


def migrate_sesiones(sqlite_conn: sqlite3.Connection, pg_session: Session) -> dict[int, int]:
    """Migra sesiones de SQLite a PostgreSQL."""
    print("Migrando sesiones...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT id, facilitador, fecha, dificultad, tipo_oponente FROM sesion")
    rows = cursor.fetchall()

    id_map = {}
    for row in rows:
        sqlite_id, facilitador, fecha, dificultad, tipo_oponente = row

        existing = pg_session.query(SesionORM).filter_by(id=sqlite_id).first()
        if existing:
            print(f"  Sesión {sqlite_id} ya existe, saltando...")
            id_map[sqlite_id] = existing.id
            continue

        sesion = SesionORM(
            id=sqlite_id,
            facilitador=facilitador,
            fecha=datetime.fromisoformat(fecha) if isinstance(fecha, str) else fecha,
            dificultad=dificultad,
            tipo_oponente=tipo_oponente,
        )
        pg_session.add(sesion)
        id_map[sqlite_id] = sqlite_id
        print(f"  Migrada sesión {sqlite_id}")

    pg_session.commit()
    return id_map


def migrate_partidas(sqlite_conn: sqlite3.Connection, pg_session: Session, usuario_id_map: dict[int, int],
                      participante_id_map: dict[int, int], sesion_id_map: dict[int, int]) -> dict[str, str]:
    """Migra partidas de SQLite a PostgreSQL.

    Retorna un mapeo de id_sqlite -> id_postgres (que son iguales, son UUIDs).
    """
    print("Migrando partidas...")
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT id, usuario_id, participante_id, sesion_id, fecha, resultado, tipo, fen, nivel, tipo_oponente, jugadas_uci
        FROM partida
    """)
    rows = cursor.fetchall()

    id_map = {}
    for row in rows:
        (sqlite_id, usuario_id, participante_id, sesion_id, fecha, resultado, tipo,
         fen, nivel, tipo_oponente, jugadas_uci) = row

        # Verificar si ya existe en PostgreSQL
        existing = pg_session.query(PartidaORM).filter_by(id=sqlite_id).first()
        if existing:
            print(f"  Partida {sqlite_id} ya existe, saltando...")
            id_map[sqlite_id] = sqlite_id
            continue

        # Mapear IDs de foreign keys
        pg_usuario_id = usuario_id_map.get(usuario_id) if usuario_id else None
        pg_participante_id = participante_id_map.get(participante_id) if participante_id else None
        pg_sesion_id = sesion_id_map.get(sesion_id) if sesion_id else None

        partida = PartidaORM(
            id=sqlite_id,
            usuario_id=pg_usuario_id,
            participante_id=pg_participante_id,
            sesion_id=pg_sesion_id,
            fecha=datetime.fromisoformat(fecha) if isinstance(fecha, str) else fecha,
            resultado=resultado,
            tipo=tipo,
            fen=fen,
            nivel=nivel,
            tipo_oponente=tipo_oponente,
            jugadas_uci=jugadas_uci or "",
        )
        pg_session.add(partida)
        id_map[sqlite_id] = sqlite_id
        print(f"  Migrada partida {sqlite_id}")

    pg_session.commit()
    return id_map


def migrate_jugadas(sqlite_conn: sqlite3.Connection, pg_session: Session, partida_id_map: dict[str, str]):
    """Migra jugadas de SQLite a PostgreSQL."""
    print("Migrando jugadas...")
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT id, partida_id, numero, fen_antes, movimiento, decidido_por, tiempo_calculo_ms, explicacion
        FROM jugada
    """)
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        (sqlite_id, partida_id, numero, fen_antes, movimiento, decidido_por,
         tiempo_calculo_ms, explicacion) = row

        # Verificar que la partida existe en PostgreSQL
        if partida_id not in partida_id_map:
            print(f"  ADVERTENCIA: Partida {partida_id} no encontrada en PG, saltando jugada {sqlite_id}")
            continue

        existing = pg_session.query(JugadaORM).filter_by(id=sqlite_id).first()
        if existing:
            print(f"  Jugada {sqlite_id} ya existe, saltando...")
            continue

        jugada = JugadaORM(
            id=sqlite_id,
            partida_id=partida_id,
            numero=numero,
            fen_antes=fen_antes,
            movimiento=movimiento,
            decidido_por=decidido_por,
            tiempo_calculo_ms=tiempo_calculo_ms,
            explicacion=explicacion,
        )
        pg_session.add(jugada)
        count += 1

    pg_session.commit()
    print(f"  Migradas {count} jugadas")


def main():
    print("=== Migración SQLite -> PostgreSQL ===")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NO CONFIGURADA')}")

    # Conectar a SQLite
    sqlite_conn = get_sqlite_connection()
    sqlite_conn.row_factory = sqlite3.Row

    # Conectar a PostgreSQL
    pg_engine = get_postgres_engine()

    # Crear tablas en PostgreSQL si no existen
    print("Creando tablas en PostgreSQL (si no existen)...")
    Base.metadata.create_all(pg_engine)

    # Crear sesión de PostgreSQL
    SessionLocal = sessionmaker(bind=pg_engine)
    pg_session = SessionLocal()

    try:
        # Migrar en orden de dependencias
        usuario_id_map = migrate_usuarios(sqlite_conn, pg_session)
        participante_id_map = migrate_participantes(sqlite_conn, pg_session)
        sesion_id_map = migrate_sesiones(sqlite_conn, pg_session)
        partida_id_map = migrate_partidas(sqlite_conn, pg_session, usuario_id_map, participante_id_map, sesion_id_map)
        migrate_jugadas(sqlite_conn, pg_session, partida_id_map)

        print("\n=== Migración completada exitosamente ===")

        # Resumen
        print(f"\nResumen:")
        print(f"  Usuarios: {len(usuario_id_map)}")
        print(f"  Participantes: {len(participante_id_map)}")
        print(f"  Sesiones: {len(sesion_id_map)}")
        print(f"  Partidas: {len(partida_id_map)}")

        # Verificar conteos
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jugada")
        jugadas_count = cursor.fetchone()[0]
        print(f"  Jugadas en SQLite: {jugadas_count}")

        pg_jugadas = pg_session.query(JugadaORM).count()
        print(f"  Jugadas en PostgreSQL: {pg_jugadas}")

    except Exception as e:
        print(f"\nERROR durante la migración: {e}")
        pg_session.rollback()
        raise
    finally:
        pg_session.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()