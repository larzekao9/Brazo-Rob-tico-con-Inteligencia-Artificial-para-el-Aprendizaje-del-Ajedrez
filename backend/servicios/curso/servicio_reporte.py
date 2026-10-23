"""Ranking de jugadores por nivel y reporte de un curso para su facilitador.

**Ranking.** Ordena por el nivel vigente del jugador (`UsuarioORM.nivel_estimado`, 0 a 20, el promedio de sus últimas
calibraciones) y desempata por la precisión promedio de sus partidas. Dos jugadores empatan en puesto solo si tienen el
mismo nivel y la misma precisión. Solo entran jugadores activos con al menos una partida calibrada; el nivel es
*provisional* hasta completar las partidas de diagnóstico (`PARTIDAS_DIAGNOSTICO`). Un jugador inscrito en un curso se
compara con su curso; uno sin curso, con los demás jugadores sin curso (los alumnos de una institución no aparecen en
el ranking general: la institución es la responsable de ellos).

**Reporte.** Para el facilitador: cuánto participa y practica el curso y si la precisión mejora, que son los indicadores de
la prueba piloto del plan de negocio, más una fila por alumno.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.modelos.tablas_orm import CalibracionORM, CursoORM, InscripcionORM, PartidaORM, UsuarioORM
from backend.servicios.calibracion.servicio_calibracion import PARTIDAS_DIAGNOSTICO
from backend.servicios.medallas import servicio_medallas

LIMITE_POR_DEFECTO = 10
LIMITE_MAXIMO = 20
DIAS_ACTIVIDAD = 7


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def nombre_publico(nombre: str) -> str:
    """`Ana María Pérez` -> `Ana P.`: el primer nombre y la inicial del último apellido, para los rankings entre jugadores."""
    partes = (nombre or "").split()
    if not partes:
        return "Jugador"
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1][0].upper()}."


def _calibraciones_por_usuario(db: Session, ids: list[int]) -> dict[int, tuple[int, float]]:
    """`usuario_id -> (partidas calibradas, precisión promedio)`; solo los que tienen al menos una."""
    if not ids:
        return {}
    filas = db.execute(
        select(CalibracionORM.usuario_id, func.count(), func.avg(CalibracionORM.precision_global))
        .where(CalibracionORM.usuario_id.in_(ids))
        .group_by(CalibracionORM.usuario_id)
    ).all()
    return {usuario_id: (int(cantidad), float(promedio or 0.0)) for usuario_id, cantidad, promedio in filas}


def _ordenar_con_puestos(jugadores: list[dict]) -> list[dict]:
    """Ordena de mejor a peor por (nivel, precisión) y asigna el puesto; los empates exactos comparten puesto."""
    jugadores.sort(key=lambda j: (-j["nivel"], -j["precision"], j["id"]))
    for j in jugadores:
        j["puesto"] = 1 + sum(1 for otro in jugadores if (otro["nivel"], otro["precision"]) > (j["nivel"], j["precision"]))
    return jugadores


def _clasificados(db: Session, candidatos: list[UsuarioORM]) -> list[dict]:
    calibradas = _calibraciones_por_usuario(db, [u.id for u in candidatos])
    jugadores = []
    for usuario in candidatos:
        if usuario.id not in calibradas or usuario.nivel_estimado is None:
            continue
        cantidad, precision = calibradas[usuario.id]
        jugadores.append(
            {
                "id": usuario.id,
                "nombre": usuario.nombre,
                "nivel": int(usuario.nivel_estimado),
                "rango": usuario.rango_estimado,
                "precision": round(precision, 1),
                "partidas_calibradas": cantidad,
                "confirmado": cantidad >= PARTIDAS_DIAGNOSTICO,
            }
        )
    return _ordenar_con_puestos(jugadores)


def _alumnos_activos_del_curso(db: Session, curso_id: int) -> list[UsuarioORM]:
    return list(
        db.scalars(
            select(UsuarioORM)
            .join(InscripcionORM, InscripcionORM.usuario_id == UsuarioORM.id)
            .where(InscripcionORM.curso_id == curso_id, UsuarioORM.activo.is_(True))
        ).all()
    )


def _jugadores_sin_curso(db: Session) -> list[UsuarioORM]:
    con_curso = select(InscripcionORM.usuario_id)
    return list(
        db.scalars(
            select(UsuarioORM).where(
                UsuarioORM.rol == "jugador", UsuarioORM.activo.is_(True), UsuarioORM.id.not_in(con_curso)
            )
        ).all()
    )


def ranking(
    db: Session,
    usuario: UsuarioORM,
    limite: int = LIMITE_POR_DEFECTO,
    curso: CursoORM | None = None,
) -> dict:
    """El ranking que le corresponde a `usuario`: el de su curso si está en uno, o el de los jugadores sin curso.

    `curso` lo fuerza un facilitador que mira el ranking de un curso (el que ya validó que puede ver). Devuelve el
    alcance, el total de clasificados, los primeros `limite` con nombre público y, si `usuario` es un jugador clasificado
    que quedó fuera de ese tope, su propia fila en `mi_puesto`.
    """
    limite = max(1, min(limite, LIMITE_MAXIMO))
    if curso is None and usuario.rol == "jugador":
        inscripcion = db.scalar(select(InscripcionORM).where(InscripcionORM.usuario_id == usuario.id))
        curso = db.get(CursoORM, inscripcion.curso_id) if inscripcion else None
    if curso is not None:
        jugadores = _clasificados(db, _alumnos_activos_del_curso(db, curso.id))
        alcance, nombre_curso = "curso", curso.nombre
    else:
        jugadores = _clasificados(db, _jugadores_sin_curso(db))
        alcance, nombre_curso = "general", None

    primeros = jugadores[:limite]
    propia = next((j for j in jugadores if j["id"] == usuario.id), None)
    mostrados = [j["id"] for j in primeros] + ([propia["id"]] if propia is not None and propia not in primeros else [])
    for id_mostrado in mostrados:  # al mirar el ranking se les otorgan las medallas que ya merecían
        servicio_medallas.evaluar_y_otorgar(db, id_mostrado)
    medallas = servicio_medallas.resumen_para_ranking(db, mostrados)

    def publico(j: dict) -> dict:
        return {
            "medallas": medallas.get(j["id"], {"total": 0, "destacadas": []}),
            "puesto": j["puesto"],
            "nombre": nombre_publico(j["nombre"]),
            "nivel": j["nivel"],
            "rango": j["rango"],
            "confirmado": j["confirmado"],
            "partidas_calibradas": j["partidas_calibradas"],
            "soy_yo": j["id"] == usuario.id,
        }

    return {
        "alcance": alcance,
        "curso": nombre_curso,
        "total": len(jugadores),
        "jugadores": [publico(j) for j in primeros],
        "mi_puesto": publico(propia) if propia is not None and propia not in primeros else None,
    }


def _inicio_de_semana(momento: datetime) -> datetime:
    dia = momento.date() - timedelta(days=momento.weekday())
    return datetime(dia.year, dia.month, dia.day)


def reporte_curso(db: Session, curso: CursoORM) -> dict:
    """Resumen y una fila por alumno del curso, para su facilitador.

    Los tres indicadores de la prueba piloto: participación (alumnos que jugaron en los últimos 7 días), práctica
    (partidas por alumno en esos 7 días) y aprendizaje, medido como la precisión de las partidas calibradas en la primera
    semana con actividad del curso frente a la última (`None` si todas cayeron en la misma semana).
    """
    alumnos = list(
        db.scalars(
            select(UsuarioORM)
            .join(InscripcionORM, InscripcionORM.usuario_id == UsuarioORM.id)
            .where(InscripcionORM.curso_id == curso.id)
            .order_by(UsuarioORM.nombre)
        ).all()
    )
    ids = [a.id for a in alumnos]
    ahora = _ahora()
    corte = ahora - timedelta(days=DIAS_ACTIVIDAD)

    jugadas: dict[int, dict] = {i: {"total": 0, "recientes": 0, "ultima": None} for i in ids}
    if ids:
        for usuario_id, iniciada_en in db.execute(
            select(PartidaORM.usuario_id, PartidaORM.iniciada_en).where(
                PartidaORM.usuario_id.in_(ids), PartidaORM.iniciada_en.is_not(None), PartidaORM.es_demostracion.is_(False)
            )
        ).all():
            datos = jugadas[usuario_id]
            datos["total"] += 1
            datos["recientes"] += 1 if iniciada_en >= corte else 0
            datos["ultima"] = iniciada_en if datos["ultima"] is None or iniciada_en > datos["ultima"] else datos["ultima"]

    clasificados = {j["id"]: j for j in _clasificados(db, [a for a in alumnos if a.activo])}
    filas = []
    for alumno in alumnos:
        datos = jugadas[alumno.id]
        clasificado = clasificados.get(alumno.id)
        filas.append(
            {
                "id": alumno.id,
                "nombre": alumno.nombre,
                "activo": alumno.activo,
                "nivel": alumno.nivel_estimado,
                "rango": alumno.rango_estimado,
                "puesto": clasificado["puesto"] if clasificado else None,
                "confirmado": clasificado["confirmado"] if clasificado else False,
                "precision": clasificado["precision"] if clasificado else None,
                "partidas": datos["total"],
                "partidas_7_dias": datos["recientes"],
                "ultima_partida": datos["ultima"],
            }
        )
    filas.sort(key=lambda f: (f["puesto"] is None, f["puesto"] or 0, f["nombre"]))

    cantidad = len(alumnos)
    activos = sum(1 for f in filas if f["partidas_7_dias"] > 0)
    partidas_recientes = sum(f["partidas_7_dias"] for f in filas)
    primera = ultima = None
    semanas: dict[datetime, list[float]] = {}
    if ids:
        for creado_en, precision in db.execute(
            select(CalibracionORM.creado_en, CalibracionORM.precision_global).where(CalibracionORM.usuario_id.in_(ids))
        ).all():
            semanas.setdefault(_inicio_de_semana(creado_en), []).append(precision)
    if len(semanas) >= 2:
        orden = sorted(semanas)
        primera = round(sum(semanas[orden[0]]) / len(semanas[orden[0]]), 1)
        ultima = round(sum(semanas[orden[-1]]) / len(semanas[orden[-1]]), 1)
    return {
        "curso": {"id": curso.id, "nombre": curso.nombre, "cupo": curso.cupo, "alumnos": cantidad},
        "resumen": {
            "alumnos_activos_7_dias": activos,
            "porcentaje_activos": round(activos / cantidad * 100, 1) if cantidad else None,
            "partidas_7_dias": partidas_recientes,
            "partidas_por_alumno_semana": round(partidas_recientes / cantidad, 2) if cantidad else None,
            "precision_primera_semana": primera,
            "precision_ultima_semana": ultima,
            "variacion_precision": round(ultima - primera, 1) if primera is not None and ultima is not None else None,
        },
        "alumnos": filas,
    }
