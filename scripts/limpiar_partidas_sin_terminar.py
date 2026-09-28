#!/usr/bin/env python3
"""Limpieza única de las partidas que quedaron sin terminar en la base real,
de antes de que existiera el ciclo de vida de partidas (Sala de Control sin
botón "iniciar" — ver `backend/servicios/partida/ciclo_vida.py`).

Por defecto es un SIMULACRO: solo imprime conteos, no borra nada. Recién
borra con `--ejecutar` (y exige `--respaldo`, para no perder nada).

Uso:
    python scripts/limpiar_partidas_sin_terminar.py
    python scripts/limpiar_partidas_sin_terminar.py --ejecutar --respaldo respaldo_20260928.json
    python scripts/limpiar_partidas_sin_terminar.py --ejecutar --respaldo respaldo.json --conservar-minutos 60

Qué borra `--ejecutar`: las partidas con `resultado IS NULL` y
`estado = 'en_curso'` — sin importar cuántas jugadas tengan (a diferencia del
barrido automático de `ciclo_vida.py`, acá se pidió empezar de cero) — junto
con sus filas de `jugada`. Conserva las terminadas. Nunca toca una partida en
demostración (`es_demostracion = True`) ni una creada/actualizada en los
últimos `--conservar-minutos` (default 30, por si alguien está jugando
justo ahora). Antes de borrar, escribe TODAS las filas que va a borrar en el
archivo de `--respaldo` (JSON legible), y borra recién después, en una sola
transacción.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.database import obtener_engine
from backend.modelos.tablas_orm import JugadaORM, PartidaORM

CONSERVAR_MINUTOS_DEFECTO = 30


def _jugadas_jugador(fila: PartidaORM) -> int:
    if not fila.jugadas_uci:
        return 0
    return (len(fila.jugadas_uci.split()) + 1) // 2


def _a_utc(momento: datetime) -> datetime:
    return momento if momento.tzinfo is not None else momento.replace(tzinfo=timezone.utc)


def _es_reciente(fila: PartidaORM, ahora: datetime, conservar_minutos: int) -> bool:
    referencia = fila.actualizada_en or fila.fecha
    if referencia is None:
        return False
    return ahora - _a_utc(referencia) <= timedelta(minutes=conservar_minutos)


def _clasificar(sin_terminar: list[PartidaORM], ahora: datetime, conservar_minutos: int) -> dict:
    demostracion: list[PartidaORM] = []
    recientes: list[PartidaORM] = []
    candidatas_sin_jugadas: list[PartidaORM] = []
    candidatas_con_jugadas: list[PartidaORM] = []

    for fila in sin_terminar:
        if fila.es_demostracion:
            demostracion.append(fila)
        elif _es_reciente(fila, ahora, conservar_minutos):
            recientes.append(fila)
        elif _jugadas_jugador(fila) == 0:
            candidatas_sin_jugadas.append(fila)
        else:
            candidatas_con_jugadas.append(fila)

    return {
        "demostracion": demostracion,
        "recientes": recientes,
        "candidatas_sin_jugadas": candidatas_sin_jugadas,
        "candidatas_con_jugadas": candidatas_con_jugadas,
    }


def _conteos(sesion, conservar_minutos: int) -> dict:
    todas = list(sesion.scalars(select(PartidaORM)))
    terminadas = [fila for fila in todas if fila.resultado is not None]
    sin_terminar = [fila for fila in todas if fila.resultado is None and fila.estado == "en_curso"]
    otras_sin_terminar = [
        fila for fila in todas if fila.resultado is None and fila.estado != "en_curso"
    ]  # ya 'abandonada' por ciclo_vida.py, por ejemplo — no las toca este script

    clasificacion = _clasificar(sin_terminar, datetime.now(timezone.utc), conservar_minutos)

    return {
        "total": len(todas),
        "terminadas": len(terminadas),
        "sin_terminar_en_curso": len(sin_terminar),
        "sin_terminar_otro_estado": len(otras_sin_terminar),
        "sin_terminar_con_0_jugadas_del_jugador": len(clasificacion["candidatas_sin_jugadas"]),
        "sin_terminar_con_jugadas": len(clasificacion["candidatas_con_jugadas"]),
        "demostracion_omitidas": len(clasificacion["demostracion"]),
        "recientes_omitidas": len(clasificacion["recientes"]),
        "candidatas_a_borrar": clasificacion["candidatas_sin_jugadas"] + clasificacion["candidatas_con_jugadas"],
    }


def _imprimir_conteos(titulo: str, conteos: dict) -> None:
    print(f"\n{titulo}")
    print(f"  total de partidas:                          {conteos['total']}")
    print(f"  terminadas (se conservan):                  {conteos['terminadas']}")
    print(f"  sin terminar, con 0 jugadas del jugador:     {conteos['sin_terminar_con_0_jugadas_del_jugador']}")
    print(f"  sin terminar, con jugadas:                   {conteos['sin_terminar_con_jugadas']}")
    print(f"  demostración (omitidas, nunca se tocan):     {conteos['demostracion_omitidas']}")
    print(f"  recientes (omitidas por --conservar-minutos):{conteos['recientes_omitidas']}")
    print(f"  candidatas a borrar en total:                {len(conteos['candidatas_a_borrar'])}")


def _fila_a_dict(fila) -> dict:
    resultado = {}
    for columna in sa_inspect(fila).mapper.column_attrs:
        valor = getattr(fila, columna.key)
        if isinstance(valor, datetime):
            valor = valor.isoformat()
        resultado[columna.key] = valor
    return resultado


def _escribir_respaldo(ruta: Path, partidas: list[PartidaORM], jugadas: list[JugadaORM]) -> None:
    contenido = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "cantidad_partidas": len(partidas),
        "cantidad_jugadas": len(jugadas),
        "partidas": [_fila_a_dict(fila) for fila in partidas],
        "jugadas": [_fila_a_dict(fila) for fila in jugadas],
    }
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")


def _ejecutar_borrado(sesion, candidatas: list[PartidaORM], ruta_respaldo: Path) -> None:
    ids = [fila.id for fila in candidatas]
    jugadas = list(sesion.scalars(select(JugadaORM).where(JugadaORM.partida_id.in_(ids)))) if ids else []

    print(f"\nEscribiendo respaldo en {ruta_respaldo} ({len(candidatas)} partidas, {len(jugadas)} jugadas)...")
    _escribir_respaldo(ruta_respaldo, candidatas, jugadas)

    print("Borrando en una transacción...")
    for jugada in jugadas:
        sesion.delete(jugada)
    for fila in candidatas:
        sesion.delete(fila)
    sesion.commit()
    print("Listo.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ejecutar", action="store_true", help="Borra de verdad. Sin esto, solo simulacro.")
    parser.add_argument("--respaldo", type=str, default=None, help="Ruta del JSON de respaldo (obligatoria con --ejecutar).")
    parser.add_argument(
        "--conservar-minutos", type=int, default=CONSERVAR_MINUTOS_DEFECTO,
        help=f"No borra partidas creadas/actualizadas hace menos de esto (default {CONSERVAR_MINUTOS_DEFECTO}).",
    )
    args = parser.parse_args(argv)

    if args.ejecutar and not args.respaldo:
        parser.error("--ejecutar requiere --respaldo RUTA.json")

    engine = obtener_engine()
    fabrica = sessionmaker(bind=engine)

    with fabrica() as sesion:
        antes = _conteos(sesion, args.conservar_minutos)
        _imprimir_conteos("Estado ANTES", antes)

        if not args.ejecutar:
            print("\nSimulacro: no se borró nada. Corré de nuevo con --ejecutar --respaldo RUTA.json para borrar.")
            return

        _ejecutar_borrado(sesion, antes["candidatas_a_borrar"], Path(args.respaldo))

    with fabrica() as sesion:
        despues = _conteos(sesion, args.conservar_minutos)
        _imprimir_conteos("Estado DESPUÉS", despues)


if __name__ == "__main__":
    main()
