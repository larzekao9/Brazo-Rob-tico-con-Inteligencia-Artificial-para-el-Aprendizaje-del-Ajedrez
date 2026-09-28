"""Dataset de partidas para reentrenar el modelo propio (HU4 — todavía sin
construir; esto arma la materia prima). Panel del facilitador:
`GET /entrenamiento/estado` + `POST /entrenamiento/dataset`
(`backend/rutas/ruta_entrenamiento.py`).

Vive en `servicios/entrenamiento/`, separado a propósito de
`servicios/aprendizaje/` (la inferencia del modelo propio, HU4): acá no se
carga el modelo ni `torch`, solo se arma un ZIP con SQL/CSV/PGN a partir de
lo que ya hay en la base — el reentrenamiento en sí es otro paso, posterior.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import fecha_a_iso
from backend.modelos.tablas_orm import CalibracionORM, ExportacionDatasetORM, JugadaORM, PartidaORM, UsuarioORM
from backend.servicios.auth.servicio_auth import SECRET_KEY
from backend.servicios.calibracion import MIN_JUGADAS_PARTIDA_VALIDA

UMBRAL_PARTIDAS_ENTRENAMIENTO_DEFECTO = 10
"""Valor por defecto de la variable de entorno `UMBRAL_PARTIDAS_ENTRENAMIENTO`
(ver `.env.example`) — cuántas partidas nuevas hacen falta para que el panel
del facilitador marque `listo_para_entrenar`."""

FORMATO_DATASET = "pgn+csv"
VERSION_FORMATO_DATASET = "1.0"

_RAIZ = Path(__file__).resolve().parents[3]
_CARPETA_CHECKPOINTS = _RAIZ / "training" / "checkpoints"
_CHECKPOINT_POR_DEFECTO = "modelo_jugadas_v1_2026-09-14.pt"
"""Mismo criterio que `_obtener_checkpoint_por_defecto` de
`backend/servicios/aprendizaje/inferencia.py`, replicado acá con `pathlib` en
vez de importado: ese módulo importa `torch` al cargarse, y esta ruta no debe
pagar ese costo solo para mostrar el nombre del checkpoint vigente."""

COLUMNAS_JUGADAS = [
    "partida", "numero", "quien", "fen_antes", "movimiento_uci", "movimiento_san",
    "nivel_jugador", "rango_jugador", "tipo_oponente", "nivel_oponente", "resultado",
    "evaluacion_cp", "mate_en", "evaluacion_mejor_cp", "mate_en_mejor",
]

COLUMNAS_PARTIDAS = [
    "partida", "jugador", "fecha", "resultado", "tipo_oponente", "nivel_oponente",
    "jugadas_jugador", "precision_jugador", "nivel_jugador",
]


class SinPartidasValidasError(Exception):
    """No hay ninguna partida válida (o ninguna nueva) para exportar — la
    ruta la traduce a 409, no al 400 habitual de `ValueError`."""


def _umbral_partidas() -> int:
    valor = os.environ.get("UMBRAL_PARTIDAS_ENTRENAMIENTO")
    if not valor:
        return UMBRAL_PARTIDAS_ENTRENAMIENTO_DEFECTO
    try:
        return int(valor)
    except ValueError:
        return UMBRAL_PARTIDAS_ENTRENAMIENTO_DEFECTO


def _modelo_actual() -> str | None:
    """Nombre del checkpoint que usa Turing por defecto, o `None` si no hay
    ninguno todavía (checkpoint fuera del repo, o proyecto recién clonado)."""
    candidato: Path | None = None
    if _CARPETA_CHECKPOINTS.exists():
        checkpoints = sorted(_CARPETA_CHECKPOINTS.glob("modelo_jugadas_v*.pt"))
        if checkpoints:
            candidato = checkpoints[-1]
    if candidato is None:
        candidato = _CARPETA_CHECKPOINTS / _CHECKPOINT_POR_DEFECTO
    return candidato.name if candidato.exists() else None


def _jugadas_jugador_de(fila: PartidaORM) -> int:
    """Cuántas de las jugadas de esta fila son del humano — mismo cálculo
    que `Partida.jugadas_jugador` (el jugador siempre mueve primero), pero a
    partir de `jugadas_uci` en vez de un `chess.Board` en memoria."""
    if not fila.jugadas_uci:
        return 0
    return (len(fila.jugadas_uci.split()) + 1) // 2


def _fecha_referencia(fila: PartidaORM) -> datetime:
    """`actualizada_en`, o `fecha` si es nula — siempre en UTC explícito
    (ver `backend.database.fecha_a_iso`: las columnas TIMESTAMP de este
    proyecto no llevan zona, pero la sesión de Postgres está fijada a UTC)."""
    momento = fila.actualizada_en or fila.fecha
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento


def partidas_validas(db: Session) -> list[PartidaORM]:
    """Partidas "válidas para entrenar" (ver también `servicio_calibracion`,
    que usa el mismo mínimo de jugadas para la calibración de nivel):
    `estado == "terminada"`, al menos `MIN_JUGADAS_PARTIDA_VALIDA` jugadas
    del jugador humano, y dueño con rol `jugador` — nunca una partida de
    prueba de un facilitador."""
    filas = db.scalars(
        select(PartidaORM)
        .join(UsuarioORM, PartidaORM.usuario_id == UsuarioORM.id)
        .where(PartidaORM.estado == "terminada", UsuarioORM.rol == "jugador")
    ).all()
    return [fila for fila in filas if _jugadas_jugador_de(fila) >= MIN_JUGADAS_PARTIDA_VALIDA]


def _ultima_exportacion(db: Session) -> ExportacionDatasetORM | None:
    return db.scalar(select(ExportacionDatasetORM).order_by(ExportacionDatasetORM.id.desc()).limit(1))


def _partidas_nuevas(db: Session, validas: list[PartidaORM]) -> list[PartidaORM]:
    """Partidas válidas posteriores al `corte_en` de la última descarga —
    todas las válidas, si nunca se descargó nada."""
    ultima = _ultima_exportacion(db)
    if ultima is None:
        return validas
    corte = ultima.corte_en
    if corte.tzinfo is None:
        corte = corte.replace(tzinfo=timezone.utc)
    return [fila for fila in validas if _fecha_referencia(fila) > corte]


def estado_entrenamiento(db: Session) -> dict[str, Any]:
    """Forma exacta de `EstadoEntrenamientoResponse` (`GET /entrenamiento/estado`)."""
    validas = partidas_validas(db)
    nuevas = _partidas_nuevas(db, validas)
    umbral = _umbral_partidas()
    ultima = _ultima_exportacion(db)

    ultima_descarga = None
    if ultima is not None:
        facilitador = db.get(UsuarioORM, ultima.usuario_id)
        ultima_descarga = {
            "fecha": fecha_a_iso(ultima.creado_en),
            "cantidad_partidas": ultima.cantidad_partidas,
            "cantidad_jugadas": ultima.cantidad_jugadas,
            "facilitador": facilitador.nombre if facilitador else None,
        }

    return {
        "umbral_partidas": umbral,
        "minimo_jugadas_por_partida": MIN_JUGADAS_PARTIDA_VALIDA,
        "partidas_validas_total": len(validas),
        "partidas_nuevas": len(nuevas),
        "jugadas_jugador_nuevas": sum(_jugadas_jugador_de(fila) for fila in nuevas),
        "progreso": min(1.0, len(nuevas) / umbral) if umbral > 0 else 1.0,
        "listo_para_entrenar": len(nuevas) >= umbral if umbral > 0 else True,
        "ultima_descarga": ultima_descarga,
        "modelo_actual": _modelo_actual(),
    }


def _alias_jugador(usuario_id: int) -> str:
    """Alias anónimo y estable del jugador: nunca su nombre, correo ni id
    real. `HMAC-SHA256` (no un hash simple) para que nadie pueda reconstruir
    qué `usuario_id` corresponde a qué alias probando ids al azar sin
    conocer `JWT_SECRET_KEY`."""
    digesto = hmac.new(SECRET_KEY.encode("utf-8"), str(usuario_id).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"j_{digesto[:8]}"


def _nombre_oponente(tipo_oponente: str, nivel: int) -> str:
    if tipo_oponente == "motor":
        return f"Stockfish (nivel {nivel})"
    if tipo_oponente == "modelo":
        return f"Turing (nivel {nivel})"
    return f"{tipo_oponente.capitalize()} (nivel {nivel})"


def _construir_pgn(fila: PartidaORM, alias: str, calibracion: CalibracionORM | None) -> chess.pgn.Game:
    game = chess.pgn.Game()
    fen_inicial = fila.fen_inicial or chess.STARTING_FEN
    board = chess.Board(fen_inicial)
    game.setup(board)  # agrega SetUp/FEN solo si `fen_inicial` no es la estándar

    game.headers["Event"] = "Sistema Tutor Inteligente de Ajedrez"
    game.headers["Site"] = "local"
    game.headers["Date"] = fila.fecha.strftime("%Y.%m.%d") if fila.fecha else "????.??.??"
    game.headers["Round"] = "-"
    game.headers["White"] = f"Jugador {alias}"
    game.headers["Black"] = _nombre_oponente(fila.tipo_oponente, fila.nivel)
    game.headers["Result"] = fila.resultado or "*"
    game.headers["TipoOponente"] = fila.tipo_oponente
    game.headers["NivelOponente"] = str(fila.nivel)
    if calibracion is not None:
        game.headers["NivelJugador"] = str(calibracion.nivel_partida)
        game.headers["PrecisionJugador"] = f"{calibracion.precision_global:.2f}"

    nodo = game
    for jugada_uci in fila.jugadas_uci.split():
        movimiento = board.parse_uci(jugada_uci)
        nodo = nodo.add_variation(movimiento)
        board.push(movimiento)
    return game


def _filas_csv_jugadas(
    fila: PartidaORM, jugadas: list[JugadaORM], calibracion: CalibracionORM | None
) -> list[dict[str, Any]]:
    nivel_jugador = calibracion.nivel_partida if calibracion is not None else ""
    rango_jugador = calibracion.rango_partida if calibracion is not None else ""
    filas_csv = []
    for jugada in jugadas:
        board = chess.Board(jugada.fen_antes)
        movimiento_san = board.san(board.parse_uci(jugada.movimiento))
        filas_csv.append({
            "partida": fila.id,
            "numero": jugada.numero,
            "quien": jugada.decidido_por or "",
            "fen_antes": jugada.fen_antes,
            "movimiento_uci": jugada.movimiento,
            "movimiento_san": movimiento_san,
            "nivel_jugador": nivel_jugador,
            "rango_jugador": rango_jugador,
            "tipo_oponente": fila.tipo_oponente,
            "nivel_oponente": fila.nivel,
            "resultado": fila.resultado or "",
            "evaluacion_cp": jugada.evaluacion_cp if jugada.evaluacion_cp is not None else "",
            "mate_en": jugada.mate_en if jugada.mate_en is not None else "",
            "evaluacion_mejor_cp": jugada.evaluacion_mejor_cp if jugada.evaluacion_mejor_cp is not None else "",
            "mate_en_mejor": jugada.mate_en_mejor if jugada.mate_en_mejor is not None else "",
        })
    return filas_csv


def _fila_csv_partida(
    fila: PartidaORM, alias: str, jugadas_jugador: int, calibracion: CalibracionORM | None
) -> dict[str, Any]:
    return {
        "partida": fila.id,
        "jugador": alias,
        "fecha": fecha_a_iso(fila.fecha),
        "resultado": fila.resultado or "",
        "tipo_oponente": fila.tipo_oponente,
        "nivel_oponente": fila.nivel,
        "jugadas_jugador": jugadas_jugador,
        "precision_jugador": f"{calibracion.precision_global:.2f}" if calibracion is not None else "",
        "nivel_jugador": calibracion.nivel_partida if calibracion is not None else "",
    }


def _csv_bytes(columnas: list[str], filas: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=columnas)
    escritor.writeheader()
    escritor.writerows(filas)
    return ("﻿" + buffer.getvalue()).encode("utf-8")  # BOM: para que Excel detecte UTF-8 solo


def _leeme_txt() -> str:
    return (
        "QUÉ ES ESTE ARCHIVO\n"
        "-------------------\n"
        "Es un paquete con partidas jugadas en el Sistema Tutor Inteligente de Ajedrez. Se arma\n"
        "para el equipo técnico, como materia prima para reentrenar más adelante al modelo propio\n"
        "del sistema (Turing) — ese reentrenamiento todavía NO existe ni es automático: esta\n"
        "descarga solo junta los datos que va a necesitar el día que se construya.\n\n"
        "QUÉ CONTIENE CADA ARCHIVO\n"
        "--------------------------\n"
        "- partidas.pgn: las partidas completas, en el formato estándar de ajedrez (PGN). Se puede\n"
        "  abrir con cualquier programa o sitio de ajedrez (por ejemplo lichess.org/paste).\n"
        "- jugadas.csv: el detalle de cada jugada de cada partida, una fila por jugada, con la\n"
        "  evaluación de Stockfish. Se abre con Excel o Google Sheets.\n"
        "- partidas.csv: un resumen de una fila por partida.\n"
        "- manifiesto.json: datos técnicos de esta descarga en particular (cuántas partidas, cuándo\n"
        "  se generó, qué criterio se usó para elegirlas).\n\n"
        "LOS DATOS SON ANÓNIMOS\n"
        "------------------------\n"
        "Ningún archivo tiene nombres reales, correos, ni ningún otro dato que identifique a un\n"
        "jugador. Cada jugador aparece con un código corto (por ejemplo \"j_3f9a1c2b\") que no se\n"
        "puede revertir a su identidad real.\n\n"
        "QUÉ HACER CON ESTO\n"
        "-------------------\n"
        "Entregar este archivo, tal cual, al equipo técnico para el reentrenamiento del modelo.\n"
    )


def _empaquetar_zip(
    pgn_texto: str,
    filas_jugadas: list[dict[str, Any]],
    filas_partidas: list[dict[str, Any]],
    manifiesto: dict[str, Any],
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archivo_zip:
        archivo_zip.writestr("partidas.pgn", pgn_texto)
        archivo_zip.writestr("jugadas.csv", _csv_bytes(COLUMNAS_JUGADAS, filas_jugadas))
        archivo_zip.writestr("partidas.csv", _csv_bytes(COLUMNAS_PARTIDAS, filas_partidas))
        archivo_zip.writestr("manifiesto.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
        archivo_zip.writestr("LEEME.txt", _leeme_txt())
    return buffer.getvalue()


def generar_dataset(db: Session, facilitador_id: int, solo_nuevas: bool) -> tuple[bytes, str]:
    """Arma el ZIP del dataset y registra la descarga en `exportacion_dataset`.

    Devuelve `(contenido_zip, nombre_archivo)`. Las abandonadas nunca entran
    (`partidas_validas` solo mira `estado == "terminada"`).

    Raises:
        SinPartidasValidasError: si no hay ninguna partida válida (o
            ninguna nueva, con `solo_nuevas=True`) para exportar.
    """
    todas_validas = partidas_validas(db)
    filas = _partidas_nuevas(db, todas_validas) if solo_nuevas else todas_validas
    if not filas:
        detalle = (
            "No hay partidas nuevas desde la última descarga"
            if solo_nuevas
            else "Todavía no hay ninguna partida válida para exportar"
        )
        raise SinPartidasValidasError(detalle)

    partes_pgn: list[str] = []
    filas_csv_jugadas: list[dict[str, Any]] = []
    filas_csv_partidas: list[dict[str, Any]] = []
    cantidad_jugadas_total = 0

    for fila in filas:
        alias = _alias_jugador(fila.usuario_id)
        calibracion = db.scalar(
            select(CalibracionORM).where(
                CalibracionORM.usuario_id == fila.usuario_id, CalibracionORM.partida_id == fila.id
            )
        )
        jugadas = list(
            db.scalars(select(JugadaORM).where(JugadaORM.partida_id == fila.id).order_by(JugadaORM.numero))
        )
        jugadas_jugador = sum(1 for jugada in jugadas if jugada.decidido_por == "jugador")
        cantidad_jugadas_total += jugadas_jugador

        game = _construir_pgn(fila, alias, calibracion)
        partes_pgn.append(str(game))

        filas_csv_jugadas.extend(_filas_csv_jugadas(fila, jugadas, calibracion))
        filas_csv_partidas.append(_fila_csv_partida(fila, alias, jugadas_jugador, calibracion))

    corte_en = max(_fecha_referencia(fila) for fila in filas)

    manifiesto = {
        "version_formato": VERSION_FORMATO_DATASET,
        "generado_en": fecha_a_iso(datetime.now(timezone.utc)),
        "cantidad_partidas": len(filas),
        "cantidad_jugadas": cantidad_jugadas_total,
        "umbral_partidas": _umbral_partidas(),
        "solo_nuevas": solo_nuevas,
        "modelo_actual": _modelo_actual(),
        "criterio_validez": (
            f"Partida con estado 'terminada', con al menos {MIN_JUGADAS_PARTIDA_VALIDA} jugadas del "
            "jugador humano, y cuyo dueño tiene rol 'jugador'."
        ),
    }

    contenido_zip = _empaquetar_zip("\n\n".join(partes_pgn) + "\n", filas_csv_jugadas, filas_csv_partidas, manifiesto)

    db.add(
        ExportacionDatasetORM(
            usuario_id=facilitador_id,
            corte_en=corte_en.replace(tzinfo=None),
            cantidad_partidas=len(filas),
            cantidad_jugadas=cantidad_jugadas_total,
            formato=FORMATO_DATASET,
        )
    )
    db.commit()

    nombre_archivo = f"dataset_ajedrez_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.zip"
    return contenido_zip, nombre_archivo
