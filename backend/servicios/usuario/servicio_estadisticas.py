"""Estadísticas del jugador (HU14): agrega al vuelo sobre `partida` y `jugada`
del usuario autenticado.

Decisión ya tomada en `COORDINACION_PARALELA_BACKEND_FLUTTER.md` (sección
4.3): no hay una tabla `usuario_estadisticas` separada para mantener
sincronizada — con el volumen de partidas de una demo académica, agregar con
SQL en cada pedido no es un problema de performance, y evita que las
estadísticas queden desactualizadas.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import fecha_a_iso
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


def _perdida(
    evaluacion_cp: int | None,
    evaluacion_mejor_cp: int | None,
    mate_en: int | None,
    mate_en_mejor: int | None,
) -> int | None:
    """Cuánto valor perdió el humano respecto a la mejor jugada de Stockfish.

    Devuelve `None` si falta la evaluación (cp o mate) de la jugada realmente
    jugada o de la mejor jugada — sin ambas no se puede cuantificar la
    pérdida. Unifica casos con mate a través de `_puntaje`, lo que cubre
    tanto "había mate a favor y no se jugó" como "la jugada llevó directo a
    que lo maten", sin tratarlos como casos aparte.
    """
    if evaluacion_cp is None and mate_en is None:
        return None
    if evaluacion_mejor_cp is None and mate_en_mejor is None:
        return None
    # Nunca negativa: si la jugada guardada supera a la 'mejor' guardada, la pérdida es 0.
    return max(0, _puntaje(evaluacion_mejor_cp, mate_en_mejor) - _puntaje(evaluacion_cp, mate_en))


def _clasificar_jugada(
    evaluacion_cp: int | None,
    evaluacion_mejor_cp: int | None,
    mate_en: int | None,
    mate_en_mejor: int | None,
) -> str | None:
    """Clasifica una jugada del humano comparándola contra la mejor jugada de Stockfish.

    Umbrales estándar de análisis (Lichess/Chess.com): blunder > 300 cp,
    error > 100 cp, inexactitud > 50 cp.
    """
    perdida = _perdida(evaluacion_cp, evaluacion_mejor_cp, mate_en, mate_en_mejor)
    if perdida is None:
        return None
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


def _calcular_precision_promedio(db: Session, usuario_id: int) -> float:
    """Porcentaje de jugadas del humano "acertadas" en partidas terminadas.

    Cuenta como acierto toda jugada analizada cuya pérdida contra la mejor
    jugada de Stockfish no supere `UMBRAL_INEXACTITUD` (o sea, quedó a 50 cp
    o menos de la mejor jugada). Usa exactamente el mismo filtro que
    `_calcular_top_errores` (partidas finalizadas + `decidido_por ==
    "jugador"` + ambas evaluaciones presentes), así que la precisión y el
    `top_errores` se refieren al mismo conjunto de jugadas. Devuelve 0.0 si
    todavía no hay ninguna jugada analizada.
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

    perdidas: list[int] = []
    for fila in filas:
        perdida = _perdida(
            fila.evaluacion_cp, fila.evaluacion_mejor_cp, fila.mate_en, fila.mate_en_mejor
        )
        if perdida is not None:
            perdidas.append(perdida)
    if not perdidas:
        return 0.0

    aciertos = sum(1 for perdida in perdidas if perdida <= UMBRAL_INEXACTITUD)
    return round(aciertos / len(perdidas) * 100, 2)


SEMANAS_DEL_PROGRESO = 8
"""Cuántas semanas (la actual incluida) muestra el gráfico de progreso."""


def _inicio_de_semana(dia: date) -> date:
    """El lunes de la semana de `dia`."""
    return dia - timedelta(days=dia.weekday())


def _a_fecha(valor: object) -> date | None:
    """Pasa lo que guarda `PartidaORM.fecha` (datetime, o texto en SQLite) a una fecha."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor[:19]).date()
        except ValueError:
            return None
    return None


def armar_progreso_semanal(
    partidas: list[tuple[date, str | None]],
    jugadas: list[tuple[date, int]],
    hoy: date,
    semanas: int = SEMANAS_DEL_PROGRESO,
) -> list[dict]:
    """Agrupa por semana (lunes a domingo) las partidas jugadas y la precisión del jugador.

    `partidas` son `(fecha, resultado)` de partidas con jugadas del jugador; `jugadas` son
    `(fecha de su partida, pérdida en cp)` de jugadas ya analizadas. Devuelve siempre
    `semanas` filas, de la más vieja a la actual, incluso las vacías (así el gráfico no
    se "salta" semanas). `precision` es `None` si esa semana no tiene jugadas analizadas:
    mostrar 0 % sería inventar un dato.
    """
    lunes_actual = _inicio_de_semana(hoy)
    inicios = [lunes_actual - timedelta(weeks=n) for n in range(semanas - 1, -1, -1)]
    por_semana = {
        inicio: {"partidas": 0, "victorias": 0, "aciertos": 0, "analizadas": 0} for inicio in inicios
    }

    for fecha, resultado in partidas:
        semana = por_semana.get(_inicio_de_semana(fecha))
        if semana is None:
            continue
        semana["partidas"] += 1
        if resultado == RESULTADO_HUMANO_GANA:
            semana["victorias"] += 1

    for fecha, perdida in jugadas:
        semana = por_semana.get(_inicio_de_semana(fecha))
        if semana is None:
            continue
        semana["analizadas"] += 1
        if perdida <= UMBRAL_INEXACTITUD:
            semana["aciertos"] += 1

    return [
        {
            "semana_inicio": inicio.isoformat(),
            "partidas": datos["partidas"],
            "victorias": datos["victorias"],
            "precision": round(datos["aciertos"] / datos["analizadas"] * 100, 1) if datos["analizadas"] else None,
        }
        for inicio, datos in por_semana.items()
    ]


def _partidas_con_jugadas_del_jugador():
    """Condición de "partida realmente jugada": tiene al menos una jugada registrada.

    El humano mueve primero, así que `jugadas_uci` no vacío implica jugada del jugador. Deja
    afuera las que la Sala de Control crea sola al abrirse y nadie juega (ver
    `obtener_historial_partidas`).
    """
    return (PartidaORM.jugadas_uci.is_not(None), PartidaORM.jugadas_uci != "")


def _calcular_partidas_por_oponente(db: Session, usuario_id: int) -> dict[str, int]:
    """Cuántas partidas realmente jugadas contra cada rival (`motor` = Stockfish, `modelo` = Turing)."""
    filas = db.execute(
        select(PartidaORM.tipo_oponente, func.count())
        .where(PartidaORM.usuario_id == usuario_id, *_partidas_con_jugadas_del_jugador())
        .group_by(PartidaORM.tipo_oponente)
    ).all()
    conteo = {"motor": 0, "modelo": 0}
    for tipo, cantidad in filas:
        conteo[tipo] = cantidad
    return conteo


def _calcular_progreso_semanal(db: Session, usuario_id: int, hoy: date | None = None) -> list[dict]:
    """Progreso de las últimas `SEMANAS_DEL_PROGRESO` semanas, desde la base (ver `armar_progreso_semanal`)."""
    hoy = hoy or date.today()
    desde = _inicio_de_semana(hoy) - timedelta(weeks=SEMANAS_DEL_PROGRESO - 1)

    partidas = []
    for fecha_bruta, resultado in db.execute(
        select(PartidaORM.fecha, PartidaORM.resultado).where(
            PartidaORM.usuario_id == usuario_id, *_partidas_con_jugadas_del_jugador()
        )
    ).all():
        fecha = _a_fecha(fecha_bruta)
        if fecha is not None and fecha >= desde:
            partidas.append((fecha, resultado))

    jugadas = []
    for fecha_bruta, cp, cp_mejor, mate, mate_mejor in db.execute(
        select(
            PartidaORM.fecha,
            JugadaORM.evaluacion_cp,
            JugadaORM.evaluacion_mejor_cp,
            JugadaORM.mate_en,
            JugadaORM.mate_en_mejor,
        )
        .join(PartidaORM, JugadaORM.partida_id == PartidaORM.id)
        .where(
            PartidaORM.usuario_id == usuario_id,
            PartidaORM.resultado.is_not(None),
            JugadaORM.decidido_por == "jugador",
        )
    ).all():
        fecha = _a_fecha(fecha_bruta)
        perdida = _perdida(cp, cp_mejor, mate, mate_mejor)
        if fecha is not None and fecha >= desde and perdida is not None:
            jugadas.append((fecha, perdida))

    return armar_progreso_semanal(partidas, jugadas, hoy)


FASES = ("apertura", "medio", "final")
PLY_FIN_APERTURA = 20
PLY_FIN_MEDIO_JUEGO = 60


def clasificar_fase(ply: int) -> str:
    """Fase de la partida según el número de jugada (ply): apertura hasta la 10.ª jugada de cada
    bando, medio juego hasta la 30.ª, y final desde ahí. Es una regla simple y fija, no una
    detección de material en el tablero: sirve para orientar, no para pretender exactitud."""
    if ply <= PLY_FIN_APERTURA:
        return "apertura"
    if ply <= PLY_FIN_MEDIO_JUEGO:
        return "medio"
    return "final"


def armar_precision_por_fase(perdidas: list[tuple[int, int]]) -> list[dict]:
    """Agrupa `(ply, pérdida en cp)` por fase. `precision` es `None` si la fase no tiene jugadas
    analizadas (no se inventa 0 %)."""
    jugadas = {fase: 0 for fase in FASES}
    aciertos = {fase: 0 for fase in FASES}
    for ply, perdida in perdidas:
        fase = clasificar_fase(ply)
        jugadas[fase] += 1
        if perdida <= UMBRAL_INEXACTITUD:
            aciertos[fase] += 1
    return [
        {
            "fase": fase,
            "jugadas": jugadas[fase],
            "precision": round(aciertos[fase] / jugadas[fase] * 100, 1) if jugadas[fase] else None,
        }
        for fase in FASES
    ]


def _calcular_precision_por_fase(db: Session, usuario_id: int) -> list[dict]:
    """Precisión del jugador en apertura, medio juego y final (jugadas analizadas de partidas terminadas)."""
    filas = db.execute(
        select(
            JugadaORM.numero,
            JugadaORM.evaluacion_cp,
            JugadaORM.evaluacion_mejor_cp,
            JugadaORM.mate_en,
            JugadaORM.mate_en_mejor,
        )
        .join(PartidaORM, JugadaORM.partida_id == PartidaORM.id)
        .where(
            PartidaORM.usuario_id == usuario_id,
            PartidaORM.resultado.is_not(None),
            JugadaORM.decidido_por == "jugador",
        )
    ).all()
    perdidas = []
    for ply, cp, cp_mejor, mate, mate_mejor in filas:
        perdida = _perdida(cp, cp_mejor, mate, mate_mejor)
        if perdida is not None:
            perdidas.append((ply, perdida))
    return armar_precision_por_fase(perdidas)


def _calcular_resultados_por_oponente(db: Session, usuario_id: int) -> dict[str, dict[str, int]]:
    """Ganadas, perdidas y tablas contra cada rival, solo de partidas terminadas y realmente jugadas."""
    filas = db.execute(
        select(PartidaORM.tipo_oponente, PartidaORM.resultado, func.count())
        .where(
            PartidaORM.usuario_id == usuario_id,
            PartidaORM.resultado.is_not(None),
            *_partidas_con_jugadas_del_jugador(),
        )
        .group_by(PartidaORM.tipo_oponente, PartidaORM.resultado)
    ).all()
    claves = {RESULTADO_HUMANO_GANA: "ganadas", RESULTADO_HUMANO_PIERDE: "perdidas", RESULTADO_TABLAS: "tablas"}
    resultado = {"motor": {"ganadas": 0, "perdidas": 0, "tablas": 0}, "modelo": {"ganadas": 0, "perdidas": 0, "tablas": 0}}
    for tipo, res, cantidad in filas:
        if tipo in resultado and res in claves:
            resultado[tipo][claves[res]] += cantidad
    return resultado


def calcular_estadisticas(db: Session, usuario_id: int) -> dict:
    """Cuenta partidas por resultado, la racha de victorias actual, la
    precisión promedio y `top_errores`.

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
        "precision_promedio": _calcular_precision_promedio(db, usuario_id),
        "top_errores": _calcular_top_errores(db, usuario_id),
        "partidas_por_oponente": _calcular_partidas_por_oponente(db, usuario_id),
        "progreso_semanal": _calcular_progreso_semanal(db, usuario_id),
        "resultados_por_oponente": _calcular_resultados_por_oponente(db, usuario_id),
        "precision_por_fase": _calcular_precision_por_fase(db, usuario_id),
    }


def obtener_historial_partidas(db: Session, usuario_id: int, limit: int, offset: int) -> dict:
    """Página del historial de partidas del usuario, más reciente primero.

    Excluye las partidas sin ninguna jugada del jugador (`jugadas_uci`
    vacío): el humano siempre mueve primero (`servicio_partida.mover`), así
    que una partida con al menos una jugada registrada tiene, por
    definición, al menos una jugada del jugador — no hace falta mirar la
    tabla `jugada` para este filtro. Son las que la Sala de Control crea
    sola al abrir la pantalla, sin botón "iniciar", y nadie llegó a jugar
    (ver `backend/servicios/partida/ciclo_vida.py`); `total` ya cuenta solo
    las que quedan tras excluirlas.
    """
    filtro = (PartidaORM.usuario_id == usuario_id, PartidaORM.jugadas_uci.is_not(None), PartidaORM.jugadas_uci != "")

    total = db.scalar(select(func.count()).select_from(PartidaORM).where(*filtro)) or 0

    filas = db.scalars(
        select(PartidaORM)
        .where(*filtro)
        .order_by(PartidaORM.fecha.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    partidas = [
        {
            "id": fila.id,
            "fecha": fecha_a_iso(fila.fecha) if hasattr(fila.fecha, "isoformat") else str(fila.fecha),
            "resultado": fila.resultado,
            "tipo_oponente": fila.tipo_oponente,
            "nivel": fila.nivel,
            "cantidad_jugadas": len(fila.jugadas_uci.split()) if fila.jugadas_uci else 0,
            "estado": fila.estado,
        }
        for fila in filas
    ]

    return {"total": total, "partidas": partidas}


# Un mate pierde una puntuación enorme; sin este tope distorsiona la pérdida media.
TOPE_PERDIDA_MEDIA_CP = 1000


def resumir_turing_por_nivel(filas: list[tuple]) -> list[dict]:
    """Agrupa las jugadas de Turing por nivel de la partida y resume cómo jugó frente a Stockfish.

    Cada fila es `(nivel, partida_id, evaluacion_cp, evaluacion_mejor_cp, mate_en, mate_en_mejor)`
    de una jugada del modelo. Por nivel: partidas y jugadas analizadas, porcentaje de jugadas a
    `UMBRAL_INEXACTITUD` cp o menos de la mejor de Stockfish (precisión), pérdida media y blunders.
    Las jugadas sin evaluación se descartan.
    """
    por_nivel: dict[int, dict] = {}
    for nivel, partida_id, evaluacion_cp, evaluacion_mejor_cp, mate_en, mate_en_mejor in filas:
        perdida = _perdida(evaluacion_cp, evaluacion_mejor_cp, mate_en, mate_en_mejor)
        if perdida is None:
            continue
        grupo = por_nivel.setdefault(nivel, {"partidas": set(), "perdidas": []})
        grupo["partidas"].add(partida_id)
        grupo["perdidas"].append(perdida)

    resultado = []
    for nivel in sorted(por_nivel):
        grupo = por_nivel[nivel]
        perdidas = grupo["perdidas"]
        aciertos = sum(1 for perdida in perdidas if perdida <= UMBRAL_INEXACTITUD)
        resultado.append({
            "nivel": nivel,
            "partidas_analizadas": len(grupo["partidas"]),
            "jugadas_analizadas": len(perdidas),
            "precision": round(aciertos / len(perdidas) * 100, 1),
            "perdida_media_cp": round(sum(min(p, TOPE_PERDIDA_MEDIA_CP) for p in perdidas) / len(perdidas), 1),
            "blunders": sum(1 for perdida in perdidas if perdida >= UMBRAL_BLUNDER),
        })
    return resultado


def calcular_turing_por_nivel(db: Session) -> list[dict]:
    """Cómo juega Turing según el nivel de la partida, frente a Stockfish (panel del facilitador).

    Solo cuenta partidas terminadas contra el modelo cuyas jugadas ya fueron analizadas con
    Stockfish: la evaluación se guarda cuando se corre el análisis completo de la partida.
    """
    filas = db.execute(
        select(
            PartidaORM.nivel,
            PartidaORM.id,
            JugadaORM.evaluacion_cp,
            JugadaORM.evaluacion_mejor_cp,
            JugadaORM.mate_en,
            JugadaORM.mate_en_mejor,
        )
        .join(JugadaORM, JugadaORM.partida_id == PartidaORM.id)
        .where(
            PartidaORM.resultado.is_not(None),
            PartidaORM.tipo_oponente == "modelo",
            JugadaORM.decidido_por == "modelo",
        )
    ).all()
    return resumir_turing_por_nivel([tuple(fila) for fila in filas])
