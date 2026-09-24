"""Servicio de Retroalimentación Técnica y Tutoría Pedagógica de Partidas (HU5/HU6).

Cumple los requisitos funcionales del proyecto:
- RF18: Comparar cada jugada del jugador contra la mejor alternativa del motor (pérdida en centipawns).
- RF19: Explicar en lenguaje comprensible qué principio de ajedrez se aplicó o debió aplicarse.
- RF20: Adaptar la retroalimentación al nivel del participante y calcular probabilidad de victoria (fórmula Lichess).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import chess

VALORES_PIEZAS = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 320,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

NOMBRES_PIEZAS = {
    chess.PAWN: "peón",
    chess.KNIGHT: "caballo",
    chess.BISHOP: "alfil",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
    chess.KING: "rey",
}

CASILLAS_CENTRALES = {chess.E4, chess.D4, chess.E5, chess.D5}
CASILLAS_CENTRO_AMPLIADO = {
    chess.C3, chess.D3, chess.E3, chess.F3,
    chess.C4, chess.D4, chess.E4, chess.F4,
    chess.C5, chess.D5, chess.E5, chess.F5,
    chess.C6, chess.D6, chess.E6, chess.F6,
}


def centipawns_a_probabilidad_victoria(cp: int | None, mate_en: int | None = None) -> float:
    """Convierte centipawns a porcentaje de victoria (0.0% a 100.0%) mediante la curva logística ajustada de Lichess.

    Fórmula oficial: Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)
    """
    if mate_en is not None:
        return 100.0 if mate_en > 0 else 0.0
    if cp is None:
        return 50.0

    val = 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)
    return round(max(0.0, min(100.0, val)), 1)


def clasificar_calidad_jugada(
    perdida_cp: int,
    es_mejor_jugada: bool,
    mate_en_antes: int | None = None,
    mate_en_despues: int | None = None,
    es_sacrificio_ganador: bool = False,
) -> str:
    """Clasifica la jugada en las categorías estándar del ajedrez digital.

    Categorías:
    - 'brillante': sacrificio posicional o táctico ventajoso.
    - 'mejor': jugada óptima idéntica al oráculo o con pérdida <= 10 cp.
    - 'excelente': pérdida entre 11 y 30 cp.
    - 'buena': pérdida entre 31 y 49 cp (sólida y aceptable).
    - 'imprecision': pérdida entre 50 y 99 cp.
    - 'error': pérdida entre 100 y 299 cp.
    - 'blunder': pérdida >= 300 cp o permitir mate rival.
    """
    if mate_en_despues is not None and mate_en_despues < 0:
        return "blunder"
    if mate_en_antes is not None and mate_en_antes > 0 and (mate_en_despues is None or mate_en_despues <= 0):
        return "blunder"

    if es_sacrificio_ganador and perdida_cp <= 15:
        return "brillante"
    if es_mejor_jugada or perdida_cp <= 10:
        return "mejor"
    if perdida_cp <= 30:
        return "excelente"
    if perdida_cp < 50:
        return "buena"
    if perdida_cp < 100:
        return "imprecision"
    if perdida_cp < 300:
        return "error"
    return "blunder"


def explicar_jugada(
    fen_antes: str,
    jugada_san: str,
    fen_despues: str,
    mejor_jugada_san: str | None,
    clasificacion: str,
    perdida_cp: int,
) -> tuple[str, str]:
    """Genera la explicación pedagógica en lenguaje natural y detecta el principio ajedrecístico involucrado.

    Returns:
        (principio_ajedrecistico, explicacion_pedagogica)
    """
    tablero_antes = chess.Board(fen_antes)
    try:
        movimiento = tablero_antes.parse_san(jugada_san)
    except ValueError:
        return "general", f"Se realizó la jugada {jugada_san}."

    tablero_despues = chess.Board(fen_despues)
    turno = tablero_antes.turn  # True = Blancas, False = Negras
    color_str = "blancas" if turno == chess.WHITE else "negras"
    pieza = tablero_antes.piece_at(movimiento.from_square)
    pieza_tipo = pieza.piece_type if pieza else chess.PAWN
    nombre_pieza = NOMBRES_PIEZAS.get(pieza_tipo, "pieza")
    casilla_destino_nombre = chess.square_name(movimiento.to_square)

    # 1. Caso de Jaque Mate
    if tablero_despues.is_checkmate():
        return "jaque_mate", f"¡Jaque mate! Remate táctico decisivo con {jugada_san} que finaliza la partida con victoria."

    # 2. Si permitió mate rival
    for m in tablero_despues.legal_moves:
        tablero_despues.push(m)
        if tablero_despues.is_checkmate():
            tablero_despues.pop()
            return "jaque_mate", f"Grave descuido: la jugada {jugada_san} deja a tu rey desprotegido ante un jaque mate forzado del rival."
        tablero_despues.pop()

    # 3. Enroque
    if tablero_antes.is_castling(movimiento):
        return "seguridad_del_rey", "¡Excelente decisión de seguridad! El enroque protege al rey y activa la torre hacia el centro."

    # 4. Pieza propia colgada (descuido táctico)
    defensores = tablero_despues.attackers(turno, movimiento.to_square)
    atacantes = tablero_despues.attackers(not turno, movimiento.to_square)
    if atacantes and (not defensores or min([VALORES_PIEZAS.get(tablero_despues.piece_at(sq).piece_type, 100) for sq in atacantes if tablero_despues.piece_at(sq)] or [100]) < VALORES_PIEZAS.get(pieza_tipo, 100)):
        if clasificacion in ("error", "blunder"):
            return "pieza_indefensa", f"Dejaste tu {nombre_pieza} en {casilla_destino_nombre} bajo ataque rival sin defensores suficientes. Era preferible retirarla o defenderla."

    # 5. Oportunidad táctica desaprovechada
    if clasificacion in ("error", "blunder", "imprecision") and mejor_jugada_san:
        try:
            mov_mejor = tablero_antes.parse_san(mejor_jugada_san)
            if tablero_antes.is_capture(mov_mejor):
                pieza_capturable = tablero_antes.piece_at(mov_mejor.to_square)
                nombre_cap = NOMBRES_PIEZAS.get(pieza_capturable.piece_type, "pieza") if pieza_capturable else "material"
                return "oportunidad_tactica", f"Se pasó por alto una oportunidad táctica: con {mejor_jugada_san} podías capturar {nombre_cap} rival con gran ventaja."
        except ValueError:
            pass

    # 6. Principios de Apertura (primeros 10 plies / movimientos)
    numero_jugada = tablero_antes.fullmove_number
    if numero_jugada <= 8:
        # Control del centro
        if movimiento.to_square in CASILLAS_CENTRALES and pieza_tipo == chess.PAWN:
            return "control_del_centro", f"Muy buena ocupación central: avanzar el peón a {casilla_destino_nombre} domina casillas estratégicas vitales."
        # Desarrollo de piezas menores
        if pieza_tipo in (chess.KNIGHT, chess.BISHOP):
            if clasificacion in ("mejor", "excelente", "buena"):
                return "desarrollo_piezas", f"Buen desarrollo: poner en juego tu {nombre_pieza} hacia {casilla_destino_nombre} mejora la armonía de tu posición."
        # Mover peones laterales en apertura descuidando desarrollo
        if pieza_tipo == chess.PAWN and movimiento.to_square not in CASILLAS_CENTRO_AMPLIADO:
            if clasificacion in ("imprecision", "error"):
                return "desarrollo_piezas", f"Mover peones de flanco en la apertura suele retrasar el desarrollo prioritario de tus caballos y alfiles."

    # 7. Jaques
    if tablero_despues.is_check():
        if clasificacion in ("mejor", "excelente", "buena", "brillante"):
            return "iniciativa_tactica", f"Jaque incisivo con {jugada_san} que obliga al rival a defenderse y ceder la iniciativa."

    # 8. Respuestas según clasificación
    if clasificacion == "brillante":
        return "maestria_tactica", f"¡Jugada brillante! Una decisión táctica de alto calibre que desarticula la posición rival."
    if clasificacion in ("mejor", "excelente"):
        return "posicion_solida", f"Jugada sólida y precisa que mantiene una posición sana y activa para las {color_str}."
    if clasificacion == "buena":
        return "posicion_solida", f"Movimiento aceptable que conserva la estabilidad de tu posición."
    if clasificacion == "imprecision":
        sug = f" La alternativa preferida era {mejor_jugada_san}." if mejor_jugada_san else ""
        return "imprecision_posicional", f"Imprecisión leve: cede una pequeña porción de ventaja.{sug}"
    if clasificacion == "error":
        sug = f" La opción recomendada era {mejor_jugada_san}." if mejor_jugada_san else ""
        return "error_tactico", f"Error táctico: deteriora tu posición y otorga iniciativa al contrincante.{sug}"
    
    sug = f" Lo más aconsejable era {mejor_jugada_san}." if mejor_jugada_san else ""
    return "colgada_grave", f"Colgada grave (blunder): concede una ventaja decisiva al adversario.{sug}"


def analizar_jugada_en_tiempo_real(
    fen_antes: str,
    jugada_san: str,
    fen_despues: str,
    evaluacion_antes_cp: int,
    evaluacion_despues_cp: int,
    mejor_jugada_san: str | None,
    mate_en_antes: int | None = None,
    mate_en_despues: int | None = None,
) -> dict[str, Any]:
    """Evalúa una jugada en vivo justo después de realizarse (para HU6 y visualización).

    Devuelve calidad, Win%, principio pedagógico y consejo inmediato en tiempo real.
    """
    # Pérdida en centipawns en perspectiva de quien jugó
    perdida_cp = max(0, evaluacion_antes_cp - evaluacion_despues_cp)
    es_mejor = (mejor_jugada_san == jugada_san) or (perdida_cp <= 5)

    clasificacion = clasificar_calidad_jugada(
        perdida_cp=perdida_cp,
        es_mejor_jugada=es_mejor,
        mate_en_antes=mate_en_antes,
        mate_en_despues=mate_en_despues,
    )

    principio, explicacion = explicar_jugada(
        fen_antes=fen_antes,
        jugada_san=jugada_san,
        fen_despues=fen_despues,
        mejor_jugada_san=mejor_jugada_san,
        clasificacion=clasificacion,
        perdida_cp=perdida_cp,
    )

    probabilidad_victoria = centipawns_a_probabilidad_victoria(evaluacion_despues_cp, mate_en_despues)

    return {
        "calidad": clasificacion,
        "perdida_cp": perdida_cp,
        "probabilidad_victoria": probabilidad_victoria,
        "principio_ajedrecistico": principio,
        "explicacion": explicacion,
        "mejor_alternativa": mejor_jugada_san,
    }


def generar_resumen_partida(analisis_jugadas: list[dict[str, Any]]) -> dict[str, Any]:
    """Genera las estadísticas globales post-partida, curva de efectividad y consejo del tutor (HU5)."""
    conteo: dict[str, int] = {
        "brillante": 0,
        "mejor": 0,
        "excelente": 0,
        "buena": 0,
        "imprecision": 0,
        "error": 0,
        "blunder": 0,
    }

    curva_efectividad: list[dict[str, Any]] = []
    puntos_ponderados = 0.0
    total_jugadas_evaluadas = 0

    pesos_calidad = {
        "brillante": 100.0,
        "mejor": 100.0,
        "excelente": 95.0,
        "buena": 80.0,
        "imprecision": 50.0,
        "error": 20.0,
        "blunder": 0.0,
    }

    for j in analisis_jugadas:
        calidad = j.get("calidad", "buena")
        if calidad in conteo:
            conteo[calidad] += 1
        
        ply = j.get("numero_ply", len(curva_efectividad) + 1)
        prob_win = j.get("probabilidad_victoria", 50.0)
        curva_efectividad.append({
            "ply": ply,
            "probabilidad_victoria": prob_win,
            "calidad": calidad,
            "jugada_san": j.get("jugada_san", ""),
        })

        puntos_ponderados += pesos_calidad.get(calidad, 50.0)
        total_jugadas_evaluadas += 1

    precision_global = round(puntos_ponderados / total_jugadas_evaluadas, 1) if total_jugadas_evaluadas > 0 else 50.0

    # Diagnóstico pedagógico global
    if conteo["blunder"] >= 2:
        consejo = (
            "Tu principal área de mejora es la visión táctica y prevención de colgadas: "
            "antes de soltar cada pieza, revisa si queda expuesta a ataques rivales directos."
        )
    elif conteo["error"] + conteo["imprecision"] >= 4:
        consejo = (
            "Mantuviste una buena actitud de ataque, pero algunas imprecisiones posicionales "
            "cedieron la iniciativa. Procura asegurar la coordinación de piezas menores antes de abrir líneas."
        )
    elif precision_global >= 80.0:
        consejo = (
            "¡Gran demostración técnica! Jugaste con alta precisión y solidez propia de un jugador experimentado. "
            "Continúa practicando la conversión rápida de ventajas en el final."
        )
    else:
        consejo = (
            "Partida balanceada. Recuerda priorizar el control del centro con peones y la seguridad de tu rey "
            "mediante un enroque oportuno en la fase de apertura."
        )

    return {
        "precision_global": precision_global,
        "conteo_calidad": conteo,
        "curva_efectividad": curva_efectividad,
        "consejo_tutor": consejo,
        "total_jugadas": total_jugadas_evaluadas,
    }
