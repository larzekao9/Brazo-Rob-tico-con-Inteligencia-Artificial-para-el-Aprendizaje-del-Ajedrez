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

RANGO_PRINCIPIANTE = "Principiante"
RANGO_INTERMEDIO = "Intermedio"
RANGO_AVANZADO = "Avanzado"
RANGOS_VALIDOS = (RANGO_PRINCIPIANTE, RANGO_INTERMEDIO, RANGO_AVANZADO)
RANGO_POR_DEFECTO = RANGO_INTERMEDIO

# RF20: variantes de texto por rango del jugador, para cada "caso" que puede
# detectar `explicar_jugada`. Un mismo `principio_ajedrecistico` (ej.
# "jaque_mate" o "desarrollo_piezas") puede cubrir más de un caso acá (dar
# mate vs. recibirlo; desarrollar una pieza vs. mover un peón de flanco en la
# apertura) porque el texto pedagógico correcto es distinto en cada situación
# aunque el principio general sea el mismo — el mapeo caso -> principio queda
# en cada punto de retorno de `explicar_jugada`, no acá. El nivel
# "Intermedio" es el texto que ya existía antes de RF20 (baseline sin tocar).
VARIANTES_POR_NIVEL: dict[str, dict[str, str]] = {
    "jaque_mate_propio": {
        RANGO_PRINCIPIANTE: "¡Ganaste! Con {jugada_san} le diste jaque mate al rey rival y la partida terminó. ¡Muy bien jugado!",
        RANGO_INTERMEDIO: "¡Jaque mate! Remate táctico decisivo con {jugada_san} que finaliza la partida con victoria.",
        RANGO_AVANZADO: "Mate forzado ejecutado con {jugada_san}: secuencia decisiva que sentencia la partida sin margen de defensa para el rival.",
    },
    "jaque_mate_rival": {
        RANGO_PRINCIPIANTE: "¡Uy! Con {jugada_san} tu rey quedó atrapado y el rival te dio jaque mate. No te preocupes, la próxima vez fijate bien si tu rey queda seguro antes de mover.",
        RANGO_INTERMEDIO: "Grave descuido: la jugada {jugada_san} deja a tu rey desprotegido ante un jaque mate forzado del rival.",
        RANGO_AVANZADO: "Blunder crítico: {jugada_san} permite mate forzado inmediato — pérdida total de la partida.",
    },
    "enroque": {
        RANGO_PRINCIPIANTE: "¡Muy bien! Enrocaste: tu rey queda más protegido, lejos del centro, y tu torre entra a jugar.",
        RANGO_INTERMEDIO: "¡Excelente decisión de seguridad! El enroque protege al rey y activa la torre hacia el centro.",
        RANGO_AVANZADO: "Enroque oportuno: mejora la seguridad del rey y conecta la torre para sumarla al juego.",
    },
    "pieza_indefensa": {
        RANGO_PRINCIPIANTE: "¡Cuidado! Tu {nombre_pieza} en {casilla_destino_nombre} quedó sola y el rival te la puede comer gratis. La próxima vez, antes de mover, fijate qué piezas tuyas quedan sin nadie que las proteja.",
        RANGO_INTERMEDIO: "Dejaste tu {nombre_pieza} en {casilla_destino_nombre} bajo ataque rival sin defensores suficientes. Era preferible retirarla o defenderla.",
        RANGO_AVANZADO: "Pieza colgada: {nombre_pieza} en {casilla_destino_nombre} sin defensa suficiente ante el ataque rival — pérdida estimada: {perdida_peones:.1f} peones. Evaluá atacantes y defensores antes de fijar la pieza en esa casilla.",
    },
    "oportunidad_tactica": {
        RANGO_PRINCIPIANTE: "¡Casi! Había una jugada mejor: con {mejor_jugada_san} le podías comer {nombre_cap} al rival gratis. Ojo la próxima vez con esas capturas.",
        RANGO_INTERMEDIO: "Se pasó por alto una oportunidad táctica: con {mejor_jugada_san} podías capturar {nombre_cap} rival con gran ventaja.",
        RANGO_AVANZADO: "Oportunidad táctica desaprovechada: {mejor_jugada_san} capturaba {nombre_cap} rival — pérdida estimada: {perdida_peones:.1f} peones respecto a la jugada elegida.",
    },
    "control_del_centro": {
        RANGO_PRINCIPIANTE: "¡Bien! Llevaste tu peón al centro del tablero (casilla {casilla_destino_nombre}). Dominar el centro te da más espacio para mover tus piezas.",
        RANGO_INTERMEDIO: "Muy buena ocupación central: avanzar el peón a {casilla_destino_nombre} domina casillas estratégicas vitales.",
        RANGO_AVANZADO: "Ocupación central correcta: el peón en {casilla_destino_nombre} controla casillas clave y facilita el desarrollo con tempo.",
    },
    "desarrollo_piezas_buena": {
        RANGO_PRINCIPIANTE: "¡Bien hecho! Sacaste tu {nombre_pieza} a jugar en {casilla_destino_nombre}. Al principio de la partida conviene mover tus piezas para que estén listas para atacar y defender.",
        RANGO_INTERMEDIO: "Buen desarrollo: poner en juego tu {nombre_pieza} hacia {casilla_destino_nombre} mejora la armonía de tu posición.",
        RANGO_AVANZADO: "Desarrollo correcto: {nombre_pieza} activa hacia {casilla_destino_nombre}, sumando a la coordinación de piezas menores en la apertura.",
    },
    "desarrollo_piezas_flanco": {
        RANGO_PRINCIPIANTE: "En la apertura conviene primero sacar a jugar tus caballos y alfiles. Mover peones de los costados ahora puede hacer que te quedes atrás.",
        RANGO_INTERMEDIO: "Mover peones de flanco en la apertura suele retrasar el desarrollo prioritario de tus caballos y alfiles.",
        RANGO_AVANZADO: "Peón de flanco en apertura: retrasa el desarrollo prioritario de piezas menores — pérdida estimada: {perdida_peones:.1f} peones de tiempo/posición.",
    },
    "iniciativa_tactica": {
        RANGO_PRINCIPIANTE: "¡Buen jaque! Con {jugada_san} ponés al rey rival en aprietos y lo obligás a responder a tu jugada.",
        RANGO_INTERMEDIO: "Jaque incisivo con {jugada_san} que obliga al rival a defenderse y ceder la iniciativa.",
        RANGO_AVANZADO: "Jaque con iniciativa: {jugada_san} fuerza la respuesta rival y cede el tempo, a favor de tu plan.",
    },
    "maestria_tactica": {
        RANGO_PRINCIPIANTE: "¡Wow, jugada increíble! Encontraste algo que no era nada fácil de ver. ¡Así se juega!",
        RANGO_INTERMEDIO: "¡Jugada brillante! Una decisión táctica de alto calibre que desarticula la posición rival.",
        RANGO_AVANZADO: "Jugada brillante: recurso táctico de alto valor (posible sacrificio) que desarticula la posición rival, por encima de la línea principal esperada.",
    },
    "posicion_solida_alta": {
        RANGO_PRINCIPIANTE: "¡Buena jugada! Mantuviste tu posición fuerte y ordenada.",
        RANGO_INTERMEDIO: "Jugada sólida y precisa que mantiene una posición sana y activa para las {color_str}.",
        RANGO_AVANZADO: "Jugada precisa: conserva la evaluación y la actividad de piezas para las {color_str}, dentro de la línea principal.",
    },
    "posicion_solida_buena": {
        RANGO_PRINCIPIANTE: "Jugada correcta, mantiene todo en orden.",
        RANGO_INTERMEDIO: "Movimiento aceptable que conserva la estabilidad de tu posición.",
        RANGO_AVANZADO: "Movimiento sólido: pérdida marginal de {perdida_peones:.1f} peones respecto a la línea principal, sin comprometer la estructura.",
    },
    "imprecision_posicional": {
        RANGO_PRINCIPIANTE: "Pequeño desliz: perdiste un poquito de ventaja, nada grave.{sug}",
        RANGO_INTERMEDIO: "Imprecisión leve: cede una pequeña porción de ventaja.{sug}",
        RANGO_AVANZADO: "Imprecisión posicional: pérdida estimada de {perdida_peones:.1f} peones.{sug}",
    },
    "error_tactico": {
        RANGO_PRINCIPIANTE: "Ese movimiento no fue el mejor: le diste ventaja al rival.{sug}",
        RANGO_INTERMEDIO: "Error táctico: deteriora tu posición y otorga iniciativa al contrincante.{sug}",
        RANGO_AVANZADO: "Error táctico: pérdida estimada de {perdida_peones:.1f} peones, cede iniciativa al rival.{sug}",
    },
    "colgada_grave": {
        RANGO_PRINCIPIANTE: "¡Cuidado! Esa jugada le regaló una ventaja grande al rival. Le pasa a todos mientras aprenden — la próxima vez fijate bien antes de mover.{sug}",
        RANGO_INTERMEDIO: "Colgada grave (blunder): concede una ventaja decisiva al adversario.{sug}",
        RANGO_AVANZADO: "Blunder (colgada grave): pérdida estimada de {perdida_peones:.1f} peones, ventaja decisiva concedida al rival.{sug}",
    },
    "general": {
        RANGO_PRINCIPIANTE: "Se jugó {jugada_san}.",
        RANGO_INTERMEDIO: "Se realizó la jugada {jugada_san}.",
        RANGO_AVANZADO: "Jugada registrada: {jugada_san}.",
    },
}

SUGERENCIAS_POR_NIVEL: dict[str, dict[str, str]] = {
    "imprecision_posicional": {
        RANGO_PRINCIPIANTE: " La próxima vez podés probar con {mejor_jugada_san}.",
        RANGO_INTERMEDIO: " La alternativa preferida era {mejor_jugada_san}.",
        RANGO_AVANZADO: " Alternativa principal: {mejor_jugada_san}.",
    },
    "error_tactico": {
        RANGO_PRINCIPIANTE: " Fijate la próxima vez en {mejor_jugada_san}, era mejor opción.",
        RANGO_INTERMEDIO: " La opción recomendada era {mejor_jugada_san}.",
        RANGO_AVANZADO: " Jugada recomendada por el motor: {mejor_jugada_san}.",
    },
    "colgada_grave": {
        RANGO_PRINCIPIANTE: " Para la próxima, animate a probar {mejor_jugada_san}.",
        RANGO_INTERMEDIO: " Lo más aconsejable era {mejor_jugada_san}.",
        RANGO_AVANZADO: " Línea principal sugerida: {mejor_jugada_san}.",
    },
}


def _texto(caso: str, rango: str, **kwargs: Any) -> str:
    """Arma el texto pedagógico de un `caso` de `explicar_jugada` para el `rango` dado.

    Si `rango` no es uno de los valores válidos, usa `RANGO_POR_DEFECTO` ("Intermedio").
    """
    variantes = VARIANTES_POR_NIVEL[caso]
    plantilla = variantes.get(rango, variantes[RANGO_POR_DEFECTO])
    return plantilla.format(**kwargs)


def _sugerencia(caso: str, rango: str, mejor_jugada_san: str | None) -> str:
    """Arma la coletilla "la alternativa era X" adaptada al rango, o "" si no hay alternativa."""
    if not mejor_jugada_san:
        return ""
    variantes = SUGERENCIAS_POR_NIVEL[caso]
    plantilla = variantes.get(rango, variantes[RANGO_POR_DEFECTO])
    return plantilla.format(mejor_jugada_san=mejor_jugada_san)


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
    rango: str = RANGO_POR_DEFECTO,
) -> tuple[str, str]:
    """Genera la explicación pedagógica en lenguaje natural y detecta el principio ajedrecístico involucrado.

    RF20: `rango` adapta el texto al nivel del jugador ("Principiante",
    "Intermedio" o "Avanzado" — mismos valores que `UsuarioORM.rango_estimado`).
    Un valor no reconocido cae en "Intermedio".

    Returns:
        (principio_ajedrecistico, explicacion_pedagogica)
    """
    perdida_peones = perdida_cp / 100

    tablero_antes = chess.Board(fen_antes)
    try:
        movimiento = tablero_antes.parse_san(jugada_san)
    except ValueError:
        return "general", _texto("general", rango, jugada_san=jugada_san)

    tablero_despues = chess.Board(fen_despues)
    turno = tablero_antes.turn  # True = Blancas, False = Negras
    color_str = "blancas" if turno == chess.WHITE else "negras"
    pieza = tablero_antes.piece_at(movimiento.from_square)
    pieza_tipo = pieza.piece_type if pieza else chess.PAWN
    nombre_pieza = NOMBRES_PIEZAS.get(pieza_tipo, "pieza")
    casilla_destino_nombre = chess.square_name(movimiento.to_square)

    # 1. Caso de Jaque Mate
    if tablero_despues.is_checkmate():
        return "jaque_mate", _texto("jaque_mate_propio", rango, jugada_san=jugada_san)

    # 2. Si permitió mate rival
    for m in tablero_despues.legal_moves:
        tablero_despues.push(m)
        if tablero_despues.is_checkmate():
            tablero_despues.pop()
            return "jaque_mate", _texto("jaque_mate_rival", rango, jugada_san=jugada_san)
        tablero_despues.pop()

    # 3. Enroque
    if tablero_antes.is_castling(movimiento):
        return "seguridad_del_rey", _texto("enroque", rango)

    # 4. Pieza propia colgada (descuido táctico)
    defensores = tablero_despues.attackers(turno, movimiento.to_square)
    atacantes = tablero_despues.attackers(not turno, movimiento.to_square)
    if atacantes and (not defensores or min([VALORES_PIEZAS.get(tablero_despues.piece_at(sq).piece_type, 100) for sq in atacantes if tablero_despues.piece_at(sq)] or [100]) < VALORES_PIEZAS.get(pieza_tipo, 100)):
        if clasificacion in ("error", "blunder"):
            return "pieza_indefensa", _texto(
                "pieza_indefensa", rango,
                nombre_pieza=nombre_pieza,
                casilla_destino_nombre=casilla_destino_nombre,
                perdida_peones=perdida_peones,
            )

    # 5. Oportunidad táctica desaprovechada
    if clasificacion in ("error", "blunder", "imprecision") and mejor_jugada_san:
        try:
            mov_mejor = tablero_antes.parse_san(mejor_jugada_san)
            if tablero_antes.is_capture(mov_mejor):
                pieza_capturable = tablero_antes.piece_at(mov_mejor.to_square)
                nombre_cap = NOMBRES_PIEZAS.get(pieza_capturable.piece_type, "pieza") if pieza_capturable else "material"
                return "oportunidad_tactica", _texto(
                    "oportunidad_tactica", rango,
                    mejor_jugada_san=mejor_jugada_san,
                    nombre_cap=nombre_cap,
                    perdida_peones=perdida_peones,
                )
        except ValueError:
            pass

    # 6. Principios de Apertura (primeros 10 plies / movimientos)
    numero_jugada = tablero_antes.fullmove_number
    if numero_jugada <= 8:
        # Control del centro
        if movimiento.to_square in CASILLAS_CENTRALES and pieza_tipo == chess.PAWN:
            return "control_del_centro", _texto(
                "control_del_centro", rango, casilla_destino_nombre=casilla_destino_nombre,
            )
        # Desarrollo de piezas menores
        if pieza_tipo in (chess.KNIGHT, chess.BISHOP):
            if clasificacion in ("mejor", "excelente", "buena"):
                return "desarrollo_piezas", _texto(
                    "desarrollo_piezas_buena", rango,
                    nombre_pieza=nombre_pieza,
                    casilla_destino_nombre=casilla_destino_nombre,
                )
        # Mover peones laterales en apertura descuidando desarrollo
        if pieza_tipo == chess.PAWN and movimiento.to_square not in CASILLAS_CENTRO_AMPLIADO:
            if clasificacion in ("imprecision", "error"):
                return "desarrollo_piezas", _texto(
                    "desarrollo_piezas_flanco", rango, perdida_peones=perdida_peones,
                )

    # 7. Jaques
    if tablero_despues.is_check():
        if clasificacion in ("mejor", "excelente", "buena", "brillante"):
            return "iniciativa_tactica", _texto("iniciativa_tactica", rango, jugada_san=jugada_san)

    # 8. Respuestas según clasificación
    if clasificacion == "brillante":
        return "maestria_tactica", _texto("maestria_tactica", rango)
    if clasificacion in ("mejor", "excelente"):
        return "posicion_solida", _texto("posicion_solida_alta", rango, color_str=color_str)
    if clasificacion == "buena":
        return "posicion_solida", _texto("posicion_solida_buena", rango, perdida_peones=perdida_peones)
    if clasificacion == "imprecision":
        sug = _sugerencia("imprecision_posicional", rango, mejor_jugada_san)
        return "imprecision_posicional", _texto(
            "imprecision_posicional", rango, perdida_peones=perdida_peones, sug=sug,
        )
    if clasificacion == "error":
        sug = _sugerencia("error_tactico", rango, mejor_jugada_san)
        return "error_tactico", _texto(
            "error_tactico", rango, perdida_peones=perdida_peones, sug=sug,
        )

    sug = _sugerencia("colgada_grave", rango, mejor_jugada_san)
    return "colgada_grave", _texto("colgada_grave", rango, perdida_peones=perdida_peones, sug=sug)


def analizar_jugada_en_tiempo_real(
    fen_antes: str,
    jugada_san: str,
    fen_despues: str,
    evaluacion_antes_cp: int,
    evaluacion_despues_cp: int,
    mejor_jugada_san: str | None,
    mate_en_antes: int | None = None,
    mate_en_despues: int | None = None,
    rango: str = RANGO_POR_DEFECTO,
) -> dict[str, Any]:
    """Evalúa una jugada en vivo justo después de realizarse (para HU6 y visualización).

    Devuelve calidad, Win%, principio pedagógico y consejo inmediato en tiempo real.
    `rango` adapta el texto al nivel del jugador (RF20) — ver `explicar_jugada`.
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
        rango=rango,
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


CONSEJOS_POR_NIVEL: dict[str, dict[str, str]] = {
    "blunders": {
        RANGO_PRINCIPIANTE: (
            "Se te escaparon algunas piezas gratis durante la partida — ¡no pasa nada, "
            "le pasa a todos al empezar! Antes de mover, date un segundo para mirar si "
            "dejás alguna pieza tuya sin nadie que la proteja."
        ),
        RANGO_INTERMEDIO: (
            "Tu principal área de mejora es la visión táctica y prevención de colgadas: "
            "antes de soltar cada pieza, revisa si queda expuesta a ataques rivales directos."
        ),
        RANGO_AVANZADO: (
            "Debilidad principal: cálculo táctico insuficiente en posiciones críticas "
            "(2 o más blunders, pérdida >= 300 cp cada uno). Trabajá patrones tácticos y "
            "una doble verificación de piezas colgadas antes de confirmar la jugada."
        ),
    },
    "errores_imprecisiones": {
        RANGO_PRINCIPIANTE: (
            "Jugaste con ganas de atacar, ¡eso está muy bien! Solo recordá revisar bien "
            "el tablero antes de mover, para no regalar ventajas pequeñas."
        ),
        RANGO_INTERMEDIO: (
            "Mantuviste una buena actitud de ataque, pero algunas imprecisiones posicionales "
            "cedieron la iniciativa. Procura asegurar la coordinación de piezas menores antes de abrir líneas."
        ),
        RANGO_AVANZADO: (
            "Acumulaste errores e imprecisiones posicionales (4 o más jugadas con pérdida "
            "entre 50 y 299 cp). Trabajá la coordinación de piezas menores y la evaluación "
            "de rupturas antes de abrir líneas."
        ),
    },
    "alta_precision": {
        RANGO_PRINCIPIANTE: (
            "¡Jugaste buenísimo! Casi todas tus jugadas fueron muy acertadas. "
            "Seguí practicando así, vas muy bien."
        ),
        RANGO_INTERMEDIO: (
            "¡Gran demostración técnica! Jugaste con alta precisión y solidez propia de un jugador experimentado. "
            "Continúa practicando la conversión rápida de ventajas en el final."
        ),
        RANGO_AVANZADO: (
            "Precisión global de {precision_global:.1f}% — nivel técnico sólido. Próximo objetivo: "
            "optimizar la conversión de finales ganados y reducir la pérdida de cp en fases de transición."
        ),
    },
    "balanceada": {
        RANGO_PRINCIPIANTE: (
            "Buena partida en general. Para la próxima, intentá ocupar el centro del tablero "
            "con tus peones y poner a salvo a tu rey enrocando pronto."
        ),
        RANGO_INTERMEDIO: (
            "Partida balanceada. Recuerda priorizar el control del centro con peones y la seguridad de tu rey "
            "mediante un enroque oportuno en la fase de apertura."
        ),
        RANGO_AVANZADO: (
            "Precisión global de {precision_global:.1f}%, dentro de un rango estándar. Reforzá el control "
            "del centro y la profilaxis de seguridad del rey (enroque temprano) para reducir la varianza posicional."
        ),
    },
}


def _consejo(caso: str, rango: str, **kwargs: Any) -> str:
    """Arma el consejo pedagógico global de `generar_resumen_partida` para el `rango` dado."""
    variantes = CONSEJOS_POR_NIVEL[caso]
    plantilla = variantes.get(rango, variantes[RANGO_POR_DEFECTO])
    return plantilla.format(**kwargs)


def generar_resumen_partida(
    analisis_jugadas: list[dict[str, Any]],
    rango: str = RANGO_POR_DEFECTO,
) -> dict[str, Any]:
    """Genera las estadísticas globales post-partida, curva de efectividad y consejo del tutor (HU5).

    RF20: `rango` adapta el consejo pedagógico al nivel del jugador ("Principiante",
    "Intermedio" o "Avanzado"). Un valor no reconocido cae en "Intermedio".

    `precision_global` y `total_jugadas` cuentan las jugadas de AMBOS bandos
    (lo que muestra la vista de análisis). Para medir el nivel del jugador eso
    no sirve: las jugadas del oponente (Stockfish o Turing) inflarían o
    hundirían la nota según qué tan fuerte fuera. Por eso además devuelve
    `precision_jugador` y `total_jugadas_jugador`, calculadas solo con las
    jugadas del humano: en una partida el humano siempre mueve primero
    (`servicio_partida.mover`), o sea los plies impares (`numero_ply` 1, 3, 5...).
    `precision_jugador` es `None` si el humano no tiene ninguna jugada evaluada.
    """
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
    puntos_jugador = 0.0
    total_jugadas_jugador = 0

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

        peso = pesos_calidad.get(calidad, 50.0)
        puntos_ponderados += peso
        total_jugadas_evaluadas += 1
        if ply % 2 == 1:
            puntos_jugador += peso
            total_jugadas_jugador += 1

    precision_global = round(puntos_ponderados / total_jugadas_evaluadas, 1) if total_jugadas_evaluadas > 0 else 50.0
    precision_jugador = round(puntos_jugador / total_jugadas_jugador, 1) if total_jugadas_jugador > 0 else None

    # Diagnóstico pedagógico global
    if conteo["blunder"] >= 2:
        consejo = _consejo("blunders", rango)
    elif conteo["error"] + conteo["imprecision"] >= 4:
        consejo = _consejo("errores_imprecisiones", rango)
    elif precision_global >= 80.0:
        consejo = _consejo("alta_precision", rango, precision_global=precision_global)
    else:
        consejo = _consejo("balanceada", rango, precision_global=precision_global)

    return {
        "precision_global": precision_global,
        "conteo_calidad": conteo,
        "curva_efectividad": curva_efectividad,
        "consejo_tutor": consejo,
        "total_jugadas": total_jugadas_evaluadas,
        "precision_jugador": precision_jugador,
        "total_jugadas_jugador": total_jugadas_jugador,
    }


# RF20 (calibración automática): mismas bandas de "nivel" (0-20, escala del
# "Skill Level" de Stockfish — ver `NIVEL_MIN`/`NIVEL_MAX` en
# `motor_ajedrez.py`) que ya agrupa el selector de dificultad de Stockfish en
# la Sala de Control del frontend, para que el número que termina en
# `nivel_estimado` sea comparable con el nivel de motor que se le puede
# ofrecer como rival al jugador.
BANDA_NIVEL_POR_RANGO: dict[str, tuple[int, int]] = {
    RANGO_PRINCIPIANTE: (0, 6),
    RANGO_INTERMEDIO: (7, 13),
    RANGO_AVANZADO: (14, 20),
}

UMBRAL_PRECISION_AVANZADO = 80.0
UMBRAL_PRECISION_INTERMEDIO = 55.0


def calcular_rango_desde_precision(precision_global: float) -> tuple[int, str]:
    """Estima `(nivel_estimado, rango_estimado)` a partir de una precisión (0-100)
    — calibración automática del nivel del jugador (RF20), pensada para
    reemplazar a la autoselección manual como fuente principal.

    Por qué el sistema calculándolo solo es preferible a que el jugador se
    autoevalúe: la autoselección (el botón "punto de partida" en Mi Perfil) es
    una opinión del jugador sobre sí mismo, y como toda autoevaluación viene
    sesgada — un principiante optimista se pone "Avanzado", o al revés. La
    precisión de las jugadas del jugador (`precision_jugador` de
    `generar_resumen_partida`) sale de comparar cada jugada real contra
    Stockfish, así que es una medición objetiva del desempeño efectivo. El
    modelo propio (Turing) no interviene en este cálculo: solo Stockfish es
    la vara de comparación. La autoselección manual sigue existiendo (vía
    `PATCH /auth/nivel-estimado`) solo para el arranque, cuando todavía no hay
    ninguna partida jugada de la cual medir nada.

    Esta función es pura y sin estado: mira UNA sola precisión. Quien la
    suaviza en el tiempo es `servicio_calibracion.registrar_calibracion`, que
    le pasa el promedio de las últimas partidas calibradas del jugador (con
    historial) en vez de la de una sola. Sigue sin ponderar por el nivel del
    rival enfrentado ni por decaimiento temporal.

    El `nivel` numérico (0-20) interpola linealmente dentro de la banda de su
    rango (`BANDA_NIVEL_POR_RANGO`) según qué tan cerca está `precision_global`
    de cada extremo del umbral — no es una medición fina, solo le da algún
    significado relativo al número dentro de su rango.
    """
    precision = max(0.0, min(100.0, precision_global))

    if precision >= UMBRAL_PRECISION_AVANZADO:
        rango = RANGO_AVANZADO
        piso_precision, techo_precision = UMBRAL_PRECISION_AVANZADO, 100.0
    elif precision >= UMBRAL_PRECISION_INTERMEDIO:
        rango = RANGO_INTERMEDIO
        piso_precision, techo_precision = UMBRAL_PRECISION_INTERMEDIO, UMBRAL_PRECISION_AVANZADO
    else:
        rango = RANGO_PRINCIPIANTE
        piso_precision, techo_precision = 0.0, UMBRAL_PRECISION_INTERMEDIO

    nivel_min, nivel_max = BANDA_NIVEL_POR_RANGO[rango]
    proporcion = (precision - piso_precision) / (techo_precision - piso_precision) if techo_precision > piso_precision else 1.0
    nivel = round(nivel_min + proporcion * (nivel_max - nivel_min))
    nivel = max(nivel_min, min(nivel_max, nivel))

    return nivel, rango
