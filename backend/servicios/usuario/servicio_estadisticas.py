"""Estadísticas del jugador (HU14): agrega al vuelo sobre `partida` (y, a
futuro, `jugada`) del usuario autenticado.

Decisión ya tomada en `COORDINACION_PARALELA_BACKEND_FLUTTER.md` (sección
4.3): no hay una tabla `usuario_estadisticas` separada para mantener
sincronizada — con el volumen de partidas de una demo académica, agregar con
SQL en cada pedido no es un problema de performance, y evita que las
estadísticas queden desactualizadas.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import PartidaORM

RESULTADO_HUMANO_GANA = "1-0"
RESULTADO_HUMANO_PIERDE = "0-1"
RESULTADO_TABLAS = "1/2-1/2"


def calcular_estadisticas(db: Session, usuario_id: int) -> dict:
    """Cuenta partidas por resultado y la racha de victorias actual del usuario.

    El humano siempre juega blancas (`backend/modelos/partida.py`), así que
    `"1-0"` es victoria del jugador y `"0-1"` es derrota, tal como los guarda
    `PartidaORM.resultado` (`None` mientras la partida sigue en curso).

    `top_errores` queda vacío por ahora a propósito: clasificar una jugada
    como inexactitud/error/blunder necesita comparar su evaluación contra la
    mejor jugada de Stockfish en esa posición, y `JugadaORM` todavía no
    guarda ninguna evaluación (esta iteración solo agregó `partida_id`,
    `numero`, `fen_antes`, `movimiento` y `decidido_por` — ver
    `repositorio_partida.RepositorioPartidasPostgres.registrar_jugada`).
    Recalcularlo acá con Stockfish en cada pedido de estadísticas sería
    exactamente el costo que se quiso evitar cacheando en `jugada`; queda
    pendiente para cuando se sume una columna de evaluación por jugada.
    """
    partidas = db.scalars(
        select(PartidaORM).where(PartidaORM.usuario_id == usuario_id).order_by(PartidaORM.fecha.desc())
    ).all()

    ganadas = sum(1 for partida in partidas if partida.resultado == RESULTADO_HUMANO_GANA)
    perdidas = sum(1 for partida in partidas if partida.resultado == RESULTADO_HUMANO_PIERDE)
    tablas = sum(1 for partida in partidas if partida.resultado == RESULTADO_TABLAS)
    finalizadas = ganadas + perdidas + tablas

    racha_victoria_actual = 0
    for partida in partidas:
        if partida.resultado is None:
            continue
        if partida.resultado != RESULTADO_HUMANO_GANA:
            break
        racha_victoria_actual += 1

    return {
        "total_partidas": len(partidas),
        "partidas_ganadas": ganadas,
        "partidas_perdidas": perdidas,
        "partidas_tablas": tablas,
        "win_percent_promedio": round(ganadas / finalizadas * 100, 2) if finalizadas else 0.0,
        "racha_victoria_actual": racha_victoria_actual,
        "top_errores": [],
    }


def obtener_historial_partidas(db: Session, usuario_id: int, limit: int, offset: int) -> dict:
    """Página del historial de partidas del usuario, más reciente primero."""
    total = (
        db.scalar(select(func.count()).select_from(PartidaORM).where(PartidaORM.usuario_id == usuario_id))
        or 0
    )

    filas = db.scalars(
        select(PartidaORM)
        .where(PartidaORM.usuario_id == usuario_id)
        .order_by(PartidaORM.fecha.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    partidas = [
        {
            "id": fila.id,
            "fecha": fila.fecha.isoformat() if hasattr(fila.fecha, "isoformat") else str(fila.fecha),
            "resultado": fila.resultado,
            "tipo_oponente": fila.tipo_oponente,
            "nivel": fila.nivel,
            "cantidad_jugadas": len(fila.jugadas_uci.split()) if fila.jugadas_uci else 0,
        }
        for fila in filas
    ]

    return {"total": total, "partidas": partidas}
