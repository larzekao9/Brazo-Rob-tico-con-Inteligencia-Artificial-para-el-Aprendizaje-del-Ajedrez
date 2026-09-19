"""Estadísticas del jugador (HU14): agrega al vuelo sobre `partida` y `jugada`
del usuario autenticado.

Decisión ya tomada en `COORDINACION_PARALELA_BACKEND_FLUTTER.md` (sección
4.3): no hay una tabla `usuario_estadisticas` separada para mantener
sincronizada — con el volumen de partidas de una demo académica, agregar con
SQL en cada pedido no es un problema de performance, y evita que las
estadísticas queden desactualizadas.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import JugadaORM, PartidaORM

RESULTADO_HUMANO_GANA = "1-0"
RESULTADO_HUMANO_PIERDE = "0-1"
RESULTADO_TABLAS = "1/2-1/2"

UMBRAL_BLUNDER = 300
UMBRAL_ERROR = 100
UMBRAL_INEXACTITUD = 50

_PUNTAJE_MATE_BASE = 100_000
"""Cota superior arbitraria para convertir un mate en un "centipawn
equivalente" y poder compararlo con evaluaciones normales (ver
`_puntaje`) — mucho más grande que cualquier evaluación real en cp, así
un mate a favor siempre pesa más que cualquier ventaja material, y un mate
en contra siempre pesa menos que cualquier desventaja material."""


def _puntaje(evaluacion_cp: int | None, mate_en: int | None) -> int:
    """Une evaluación en cp y evaluación de mate en una sola escala comparable.

    Sin esto, comparar "el humano se dejó dar mate" contra "la mejor jugada
    solo valía -80 cp" (o al revés: "había mate a favor y se perdió") necesita
    un caso especial por combinación de mate/cp. Acá un mate a favor en N
    jugadas vale más cuanto más cerca esté (mate en 1 > mate en 5), y un mate
    en contra vale menos cuanto más cerca esté — ambos muy por fuera del
    rango de una evaluación normal en centipawns.
    """
    if mate_en is not None:
        signo = 1 if mate_en > 0 else -1
        return signo * (_PUNTAJE_MATE_BASE - abs(mate_en) * 100)
    return evaluacion_cp if evaluacion_cp is not None else 0


def _clasificar_jugada(
    evaluacion_cp: int | None,
    evaluacion_mejor_cp: int | None,
    mate_en: int | None,
    mate_en_mejor: int | None,
) -> str | None:
    """Clasifica una jugada del humano comparándola contra la mejor jugada de Stockfish.

    `perdida` es cuánto valor perdió el humano respecto a la mejor jugada
    posible en esa posición, ya unificando casos con mate (ver `_puntaje`) —
    esto cubre tanto "había mate a favor y no se jugó" como "la jugada
    llevó directo a que lo maten", sin tratarlos como casos aparte.
    Umbrales estándar de análisis (Lichess/Chess.com): blunder > 300 cp,
    error > 100 cp, inexactitud > 50 cp.
    """
    if evaluacion_cp is None and mate_en is None:
        return None
    if evaluacion_mejor_cp is None and mate_en_mejor is None:
        return None

    perdida = _puntaje(evaluacion_mejor_cp, mate_en_mejor) - _puntaje(evaluacion_cp, mate_en)
    if perdida > UMBRAL_BLUNDER:
        return "blunder"
    if perdida > UMBRAL_ERROR:
        return "error"
    if perdida > UMBRAL_INEXACTITUD:
        return "inexactitud"
    return None


def _calcular_top_errores(db: Session, usuario_id: int) -> list[dict]:
    """Cuenta las jugadas del humano por categoría de error, de mayor a menor.

    Solo entran jugadas de partidas ya terminadas (`PartidaORM.resultado` no
    nulo), decididas por el jugador (no las del motor/modelo), y que ya
    pasaron por `GET /partida/{id}/analisis-completo` al menos una vez —
    identificado por tener evaluación (cp o mate) tanto en la jugada
    realmente jugada como en la mejor jugada de esa posición. Las jugadas que
    nunca se analizaron no cuentan: solo se conoce el error si alguien pidió
    ver el análisis, y eso está bien (evita recalcular Stockfish acá).
    """
    filas = db.scalars(
        select(JugadaORM)
        .join(PartidaORM, JugadaORM.partida_id == PartidaORM.id)
        .where(
            PartidaORM.usuario_id == usuario_id,
            PartidaORM.resultado.is_not(None),
            JugadaORM.decidido_por == "jugador",
        )
    ).all()

    conteo: dict[str, int] = {}
    for fila in filas:
        tipo = _clasificar_jugada(
            fila.evaluacion_cp, fila.evaluacion_mejor_cp, fila.mate_en, fila.mate_en_mejor
        )
        if tipo is not None:
            conteo[tipo] = conteo.get(tipo, 0) + 1

    return sorted(
        ({"tipo": tipo, "cantidad": cantidad} for tipo, cantidad in conteo.items()),
        key=lambda item: item["cantidad"],
        reverse=True,
    )


def calcular_estadisticas(db: Session, usuario_id: int) -> dict:
    """Cuenta partidas por resultado, la racha de victorias actual y `top_errores`.

    El humano siempre juega blancas (`backend/modelos/partida.py`), así que
    `"1-0"` es victoria del jugador y `"0-1"` es derrota, tal como los guarda
    `PartidaORM.resultado` (`None` mientras la partida sigue en curso).
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
        "top_errores": _calcular_top_errores(db, usuario_id),
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
