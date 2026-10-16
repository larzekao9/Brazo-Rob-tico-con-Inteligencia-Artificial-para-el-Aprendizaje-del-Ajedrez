"""Endpoints HTTP de aprendizaje neural: inferencia del modelo y estado del checkpoint."""
from __future__ import annotations

import time

import chess
from fastapi import APIRouter, HTTPException

from backend.esquemas.aprendizaje_esquema import (
    CalculoTuring,
    CandidataCalculo,
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
    probabilidades_legales,
)
from backend.servicios.aprendizaje.busqueda_turing import explicar_decision
from backend.servicios.estrategias.estrategia_jugada import parametros_de_busqueda
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


def _san_a_uci(tablero: chess.Board, jugada_san: str) -> str:
    """Convierte una jugada SAN ("Nf3") a UCI ("g1f3") en el tablero dado.

    Devuelve `""` si la jugada viene vacía o no es legal ahí: el UCI solo sirve para
    dibujar la flecha en el frontend, así que nunca debe romper la inferencia.
    """
    if not jugada_san:
        return ""
    try:
        return tablero.parse_san(jugada_san).uci()
    except ValueError:
        return ""


@router.post("/inferencia", response_model=InferenciaModeloResponse)
def inferencia_endpoint(request: InferenciaModeloRequest) -> InferenciaModeloResponse:
    """Ejecuta inferencia del modelo propio y compara con Stockfish."""
    try:
        inicio = time.perf_counter()
        candidatas_tuplas = predecir_top_jugadas(request.fen, top_n=3)

        candidatas = [
            CandidataModelo(jugada=jugada, probabilidad=prob)
            for jugada, prob in candidatas_tuplas
        ]
        jugada_elegida = candidatas[0].jugada if candidatas else ""

        # Misma decisión que toma Turing al jugar en modo maestro: la red propone y el cálculo de variantes corrige.
        # Stockfish no interviene (solo se usa más abajo para comparar).
        calculo = None
        profundidad, tiempo_busqueda, peso_red = parametros_de_busqueda()
        if profundidad > 0 and candidatas:
            tablero_inicial = chess.Board(request.fen)
            desglose = explicar_decision(
                tablero_inicial, probabilidades_legales(tablero_inicial), profundidad, tiempo_busqueda, peso_red
            )
            jugada_elegida = desglose["jugada"]
            calculo = CalculoTuring(
                jugada_red_sola=desglose["jugada_red_sola"],
                corrige_a_la_red=desglose["corrige_a_la_red"],
                profundidad=desglose["profundidad"],
                nodos=desglose["nodos"],
                tiempo_ms=desglose["tiempo_ms"],
                peso_red=desglose["peso_red"],
                candidatas=[
                    CandidataCalculo(
                        jugada=c["jugada"],
                        jugada_uci=c["jugada_uci"],
                        probabilidad=min(1.0, max(0.0, c["probabilidad"])),
                        calculo_cp=c["calculo_cp"],
                        puntaje=c["puntaje"],
                        mate=c["mate"],
                        elegida=c["elegida"],
                    )
                    for c in desglose["candidatas"]
                ],
            )
        latencia_ms = (time.perf_counter() - inicio) * 1000

        saliencia = calcular_saliencia(request.fen)
        atencion_por_bloque = calcular_atencion(request.fen)

        # Comparación como oráculo (regla 1 del CLAUDE.md del proyecto): nunca decide la
        # jugada, solo mide qué tan buena fue la elegida por el modelo. Mismo patrón de
        # "antes/después con signo invertido" que `servicio_partida.analisis_completo`.
        antes = analizar_posicion(request.fen, nivel=20, tiempo_limite=0.5)
        jugada_motor = antes["jugada"] or ""
        evaluacion_cp = antes["evaluacion_cp"] or 0

        tablero = chess.Board(request.fen)
        jugada_elegida_uci = _san_a_uci(tablero, jugada_elegida)
        jugada_motor_uci = _san_a_uci(tablero, jugada_motor)
        tablero.push_san(jugada_elegida)
        despues = analizar_posicion(tablero.fen(), nivel=20, tiempo_limite=0.5)
        eval_resultante_cp = 0 if despues["evaluacion_cp"] is None else -despues["evaluacion_cp"]
        diferencia_cp = evaluacion_cp - eval_resultante_cp

        comparacion = ComparacionStockfish(
            jugada_motor=jugada_motor,
            evaluacion_cp=evaluacion_cp,
            diferencia_cp=diferencia_cp,
            jugada_motor_uci=jugada_motor_uci,
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
                    elegida=(info["jugada"] == jugada_elegida) if calculo else info["elegida"],
                    evaluacion_stockfish_cp=eval_resultante_candidata_cp,
                    diferencia_cp=diferencia_candidata_cp,
                )
            )

        return InferenciaModeloResponse(
            jugada_elegida=jugada_elegida,
            jugada_elegida_uci=jugada_elegida_uci,
            candidatas=candidatas,
            candidatas_detalladas=candidatas_detalladas,
            latencia_ms=latencia_ms,
            comparacion_stockfish=comparacion,
            saliencia=saliencia,
            atencion_por_bloque=atencion_por_bloque,
            calculo=calculo,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Modelo no disponible en este entorno"
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error