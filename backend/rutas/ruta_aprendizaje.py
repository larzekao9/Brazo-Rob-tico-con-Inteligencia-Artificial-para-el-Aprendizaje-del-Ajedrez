"""Endpoints HTTP de aprendizaje neural: inferencia del modelo y estado del checkpoint."""
from __future__ import annotations

import time

import chess
from fastapi import APIRouter, HTTPException

from backend.esquemas.aprendizaje_esquema import (
    CandidataDetallada,
    CandidataModelo,
    ComparacionStockfish,
    EstadoModeloResponse,
    InferenciaModeloRequest,
    InferenciaModeloResponse,
)
from backend.servicios.aprendizaje.inferencia import (
    calcular_atencion,
    calcular_saliencia,
    estado_modelo,
    explicar_top_candidatas,
    predecir_top_jugadas,
)
from backend.servicios.motor.motor_ajedrez import analizar_posicion

router = APIRouter(prefix="/aprendizaje", tags=["aprendizaje"])


@router.get("/estado-modelo", response_model=EstadoModeloResponse)
def estado_modelo_endpoint() -> EstadoModeloResponse:
    """Devuelve metadatos del modelo entrenado si está disponible."""
    try:
        info = estado_modelo()
        return EstadoModeloResponse(
            version=info["version"],
            fecha_entrenamiento=info["fecha_entrenamiento"],
            num_clases=info["num_clases"],
            dispositivo=info["dispositivo"],
            disponible=True,
        )
    except FileNotFoundError:
        return EstadoModeloResponse(
            version=0,
            fecha_entrenamiento="",
            num_clases=0,
            dispositivo="none",
            disponible=False,
        )


@router.post("/inferencia", response_model=InferenciaModeloResponse)
def inferencia_endpoint(request: InferenciaModeloRequest) -> InferenciaModeloResponse:
    """Ejecuta inferencia del modelo propio y compara con Stockfish."""
    try:
        inicio = time.perf_counter()
        candidatas_tuplas = predecir_top_jugadas(request.fen, top_n=3)
        latencia_ms = (time.perf_counter() - inicio) * 1000

        candidatas = [
            CandidataModelo(jugada=jugada, probabilidad=prob)
            for jugada, prob in candidatas_tuplas
        ]
        jugada_elegida = candidatas[0].jugada if candidatas else ""

        saliencia = calcular_saliencia(request.fen)
        atencion_por_bloque = calcular_atencion(request.fen)

        # Comparación como oráculo (regla 1 del CLAUDE.md del proyecto): nunca decide la
        # jugada, solo mide qué tan buena fue la elegida por el modelo. Mismo patrón de
        # "antes/después con signo invertido" que `servicio_partida.analisis_completo`.
        antes = analizar_posicion(request.fen, nivel=20, tiempo_limite=0.5)
        jugada_motor = antes["jugada"] or ""
        evaluacion_cp = antes["evaluacion_cp"] or 0

        tablero = chess.Board(request.fen)
        tablero.push_san(jugada_elegida)
        despues = analizar_posicion(tablero.fen(), nivel=20, tiempo_limite=0.5)
        eval_resultante_cp = 0 if despues["evaluacion_cp"] is None else -despues["evaluacion_cp"]
        diferencia_cp = evaluacion_cp - eval_resultante_cp

        comparacion = ComparacionStockfish(
            jugada_motor=jugada_motor,
            evaluacion_cp=evaluacion_cp,
            diferencia_cp=diferencia_cp,
        )

        # Detalle completo de las top-3 candidatas REALES de la red (no solo la
        # elegida), cada una con su propio chequeo táctico y su propia evaluación de
        # Stockfish — mismo patrón "antes/después con signo invertido" de arriba,
        # repetido por candidata (la posición "antes" ya se analizó una sola vez).
        candidatas_info = explicar_top_candidatas(request.fen)
        candidatas_detalladas = []
        for info in candidatas_info:
            tablero_candidata = chess.Board(request.fen)
            tablero_candidata.push_san(info["jugada"])
            resultado_candidata = analizar_posicion(
                tablero_candidata.fen(), nivel=20, tiempo_limite=0.5
            )
            eval_candidata_cp = resultado_candidata["evaluacion_cp"]
            eval_resultante_candidata_cp = (
                None if eval_candidata_cp is None else -eval_candidata_cp
            )
            diferencia_candidata_cp = evaluacion_cp - (
                eval_resultante_candidata_cp
                if eval_resultante_candidata_cp is not None
                else 0
            )

            candidatas_detalladas.append(
                CandidataDetallada(
                    jugada=info["jugada"],
                    probabilidad=info["probabilidad"],
                    da_jaque_mate=info["da_jaque_mate"],
                    rival_tiene_mate_en_1=info["rival_tiene_mate_en_1"],
                    pieza_colgada=info["pieza_colgada"],
                    elegida=info["elegida"],
                    evaluacion_stockfish_cp=eval_resultante_candidata_cp,
                    diferencia_cp=diferencia_candidata_cp,
                )
            )

        return InferenciaModeloResponse(
            jugada_elegida=jugada_elegida,
            candidatas=candidatas,
            candidatas_detalladas=candidatas_detalladas,
            latencia_ms=latencia_ms,
            comparacion_stockfish=comparacion,
            saliencia=saliencia,
            atencion_por_bloque=atencion_por_bloque,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Modelo no disponible en este entorno"
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error