"""Orquesta partidas jugables: aplica la jugada humana y responde con la
estrategia de jugada activa.

Las partidas viven detrás de `RepositorioPartidas` (patrón Repository, sección
4.3) — en memoria del proceso por defecto, o en Postgres si `DATABASE_URL`
está seteada (`crear_repositorio_partidas`, sección 7). Quién decide la
jugada de respuesta es la estrategia que devuelva `crear_estrategia_jugada`
— hoy siempre Stockfish, mañana también el modelo propio o un jugador
humano, sin tocar este archivo (ver PLAN_IMPLEMENTACION_COMPLETO.md,
secciones 4.1 y 4.3).
"""
from __future__ import annotations

import chess

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas, crear_repositorio_partidas
from backend.servicios.estrategias.fabrica_estrategias import TIPOS_SOPORTADOS, crear_estrategia_jugada
from backend.servicios.motor.motor_ajedrez import NIVEL_MAX, analizar_posicion
from backend.servicios.retroalimentacion.servicio_retroalimentacion import (
    centipawns_a_probabilidad_victoria,
    clasificar_calidad_jugada,
    explicar_jugada,
    generar_resumen_partida,
)
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.deteccion_movimiento import detectar_jugada
from backend.servicios.vision.reconocimiento import reconocer_tablero

_repositorio: RepositorioPartidas = crear_repositorio_partidas()


def crear_partida(
    nivel: int = 20,
    tipo_oponente: str = "motor",
    fen_inicial: str | None = None,
    usuario_id: int | None = None,
) -> Partida:
    """Crea una partida nueva.

    Por defecto arranca en la posición inicial estándar. Si se pasa
    `fen_inicial` (por ejemplo, el FEN que devolvió `POST /vision/reconocer`
    al escanear un tablero físico), la partida arranca ahí en cambio — así
    se puede seguir jugando digitalmente una posición que se armó sobre un
    tablero real.

    `usuario_id` es el dueño de la partida (HU10) — lo manda `ruta_partida.py`
    a partir del token de `Authorization: Bearer` ya validado, nunca viene del
    cuerpo de la request.

    Raises:
        ValueError: si `tipo_oponente` no es un tipo soportado todavía (ver
            `fabrica_estrategias.TIPOS_SOPORTADOS`), o si `fen_inicial` no es
            un FEN válido — ambos se validan acá, al crear la partida, para
            no dejar que fallen recién en la primera jugada.
    """
    if tipo_oponente not in TIPOS_SOPORTADOS:
        raise ValueError(
            f"Tipo de oponente '{tipo_oponente}' no soportado todavía "
            f"(disponibles: {sorted(TIPOS_SOPORTADOS)})"
        )
    if fen_inicial is None:
        partida = Partida(nivel=nivel, tipo_oponente=tipo_oponente, usuario_id=usuario_id)
    else:
        try:
            tablero = chess.Board(fen_inicial)
        except ValueError as error:
            raise ValueError(f"FEN inicial inválido: {fen_inicial}") from error
        if not tablero.is_valid():
            # Puede pasar con una posición mal reconocida por visión (ej.
            # demasiadas piezas) — sintácticamente es un FEN válido, pero
            # Stockfish se cae si se lo pasamos igual (ver motor_ajedrez.py).
            raise ValueError(
                f"La posición reconocida no es válida (imposible en una partida real): {fen_inicial}"
            )
        partida = Partida(
            tablero=tablero,
            nivel=nivel,
            tipo_oponente=tipo_oponente,
            fen_inicial=fen_inicial,
            usuario_id=usuario_id,
        )
    _repositorio.guardar(partida)
    return partida


def obtener_partida(partida_id: str) -> Partida:
    """Busca una partida por id.

    Raises:
        KeyError: si no existe una partida con ese id.
    """
    return _repositorio.obtener(partida_id)


def listar_partidas() -> list[Partida]:
    """Devuelve todas las partidas jugadas mientras este proceso está corriendo.

    Es un registro real (HU8/HU11) mientras el backend sigue arriba — no
    sobrevive un reinicio, porque `RepositorioPartidasEnMemoria` no persiste
    a disco. Ver sección 4.3 y 7 de PLAN_IMPLEMENTACION_COMPLETO.md.
    """
    return _repositorio.listar()


def actualizar_permisos(partida_id: str, campos: dict, usuario_id_facilitador: int | None = None) -> Partida:
    """Activa o desactiva, por partida, funciones educativas opcionales para
    el jugador (simulación 3D, cámara del tablero físico) — decisión del
    facilitador (ver `ruta_partida.py`, que exige `get_current_facilitador`
    antes de llegar acá; esta función no vuelve a chequear el rol).

    `campos` trae solo las claves que vinieron en el request
    (`exclude_unset`, igual que `servicio_auth.actualizar_perfil`) — las que
    no vinieron quedan como estaban, no se pisan con `False`.

    `es_demostracion` es un caso especial dentro de estos mismos permisos
    togglables: a diferencia de los otros dos (que aplican sobre cualquier
    partida que el facilitador esté supervisando), transmitir en vivo solo
    tiene sentido sobre una partida propia del facilitador — activarla en la
    partida de un estudiante no tendría a quién mostrarle nada como "su"
    demostración. `usuario_id_facilitador` es quién hace el PATCH (lo manda
    `ruta_partida.py` desde el token, nunca el cuerpo del request) y se usa
    solo para esa validación. Además, como solo puede haber una
    demostración activa a la vez en todo el sistema, prenderla acá apaga
    automáticamente cualquier otra partida que la tuviera activa.

    Raises:
        KeyError: si no existe una partida con ese id.
        ValueError: si se pide `es_demostracion=True` sobre una partida que
            no es del facilitador que hace el pedido.
    """
    partida = obtener_partida(partida_id)
    if campos.get("es_demostracion") is True and partida.usuario_id != usuario_id_facilitador:
        raise ValueError(
            "Solo se puede activar la demostración en una partida propia del facilitador"
        )
    for campo, valor in campos.items():
        setattr(partida, campo, valor)
    _repositorio.guardar(partida)
    if campos.get("es_demostracion") is True:
        _apagar_otras_demostraciones(partida.id)
    return partida


def _apagar_otras_demostraciones(partida_id_activa: str) -> None:
    """Apaga `es_demostracion` en cualquier otra partida que la tuviera
    activa — solo puede haber una transmisión en vivo a la vez en todo el
    sistema (ver `actualizar_permisos`), a nivel global, no por facilitador."""
    for otra in _repositorio.listar():
        if otra.id != partida_id_activa and otra.es_demostracion:
            otra.es_demostracion = False
            _repositorio.guardar(otra)


def obtener_partida_en_demostracion() -> Partida | None:
    """Partida marcada `es_demostracion=True` ahora mismo, si hay alguna.

    Usa `listar()` en vez de un método de repositorio dedicado porque no hay
    volumen ni paginación real todavía (ver `ruta_partida.py::listar`, mismo
    criterio) — agregar un índice/consulta especial para esto sería
    sobre-ingeniería para 3 semanas de proyecto. Devuelve `None` si ninguna
    partida está en demostración (ver `GET /partida/demostracion-activa`).
    """
    for partida in _repositorio.listar():
        if partida.es_demostracion:
            return partida
    return None


def jugadas_legales_desde(partida_id: str, casilla: str) -> list[str]:
    """Devuelve las casillas destino a las que se puede mover la pieza parada en `casilla`.

    Sirve para resaltar en el tablero del frontend las jugadas válidas al
    seleccionar una pieza (HU3) — usa el tablero real de la partida, nunca
    Stockfish, así que no hace falta tener el motor corriendo.

    Raises:
        KeyError: si no existe una partida con ese id.
        ValueError: si `casilla` no es una casilla válida (ej. "e2").
    """
    partida = obtener_partida(partida_id)
    try:
        origen = chess.parse_square(casilla)
    except ValueError as error:
        raise ValueError(f"Casilla inválida: {casilla}") from error
    destinos = {
        chess.square_name(jugada.to_square)
        for jugada in partida.tablero.legal_moves
        if jugada.from_square == origen
    }
    return sorted(destinos)


def mover(partida_id: str, jugada_uci: str) -> dict:
    """Aplica la jugada del humano (UCI) y responde con la jugada de la estrategia activa.

    Las dos jugadas (humano + respuesta) se prueban sobre una copia del
    tablero, no sobre `partida.tablero` directamente: si la estrategia activa
    falla (ej. el modelo propio, HU4, devuelve una jugada SAN ilegal),
    `partida.tablero` no debe quedar con la jugada del humano aplicada pero
    sin respuesta — eso dejaría el turno trabado en el lado equivocado en el
    servidor mientras el cliente, que solo vio un error, sigue mostrando la
    posición de antes. Solo se pisa `partida.tablero` si todo salió bien.

    Una vez aplicada, registra una fila en `jugada` (RF34/HU4) por cada
    jugada real que se jugó en esta llamada — la del humano y, si la partida
    no terminó ahí, la de la estrategia que respondió — vía
    `RepositorioPartidas.registrar_jugada`. Con `RepositorioPartidasEnMemoria`
    (sin `DATABASE_URL`) es un no-op documentado: no hay tabla `jugada` en
    memoria a la que escribir.

    Raises:
        KeyError: si no existe una partida con ese id.
        ValueError: si la partida ya terminó o la jugada es inválida/ilegal.
    """
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")

    try:
        jugada_humano = partida.tablero.parse_uci(jugada_uci)
    except ValueError as error:
        raise ValueError(f"Jugada inválida: {jugada_uci}") from error

    tablero_intento = partida.tablero.copy()
    fen_antes_humano = tablero_intento.fen()
    tablero_intento.push(jugada_humano)
    jugadas_a_registrar = [
        (len(tablero_intento.move_stack), fen_antes_humano, jugada_humano.uci(), "jugador")
    ]

    jugada_motor_san = None
    if not tablero_intento.is_game_over():
        estrategia = crear_estrategia_jugada(partida.tipo_oponente, nivel=partida.nivel)
        fen_antes_motor = tablero_intento.fen()
        jugada_motor_san = estrategia.decidir_jugada(fen_antes_motor)
        tablero_intento.push_san(jugada_motor_san)
        jugadas_a_registrar.append((
            len(tablero_intento.move_stack),
            fen_antes_motor,
            tablero_intento.move_stack[-1].uci(),
            partida.tipo_oponente,
        ))

    partida.tablero = tablero_intento
    _repositorio.guardar(partida)
    for numero, fen_antes, movimiento, decidido_por in jugadas_a_registrar:
        _repositorio.registrar_jugada(partida.id, numero, fen_antes, movimiento, decidido_por)

    # Analizar la posición resultante de la jugada humana para obtener variantes candidatas
    # y retroalimentación pedagógica en vivo (HU6)
    variantes_candidatas: list[dict] = []
    retroalimentacion_en_vivo: dict | None = None
    if not partida.terminada and jugada_motor_san is not None:
        analisis = analizar_posicion(partida.fen, partida.nivel)
        variantes_candidatas = analisis.get("variantes_candidatas", [])

        eval_cp = analisis.get("evaluacion_cp")
        mate_en = analisis.get("mate_en")
        prob_win = centipawns_a_probabilidad_victoria(eval_cp, mate_en)
        retroalimentacion_en_vivo = {
            "calidad": "buena",
            "perdida_cp": 0,
            "probabilidad_victoria": prob_win,
            "principio_ajedrecistico": "posicion_activa",
            "explicacion": f"Posición activa con {prob_win:.1f}% de probabilidad de victoria.",
            "mejor_alternativa": analisis.get("jugada"),
        }

    return {
        "fen": partida.fen,
        "jugada_motor": jugada_motor_san,
        "terminada": partida.terminada,
        "resultado": partida.resultado,
        "jugadas": partida.jugadas_san,
        "variantes_candidatas": variantes_candidatas,
        "retroalimentacion_en_vivo": retroalimentacion_en_vivo,
    }


def mover_desde_foto(partida_id: str) -> dict:
    """Detecta la jugada hecha en el tablero físico (RF11) y la aplica igual que `mover()`.

    Flujo: (1) el FEN actual de la partida es la posición "antes"; (2) saca
    una foto nueva de la cámara fija; (3) la reconoce a FEN ("después");
    (4) `detectar_jugada` prueba todas las jugadas legales desde "antes" y
    devuelve cuál reproduce "después" exactamente; (5) se aplica con la
    misma lógica que una jugada hecha a clics (incluida la respuesta de la
    estrategia activa).

    Raises:
        KeyError: si no existe una partida con ese id.
        RuntimeError: si no se pudo capturar la foto (cámara).
        FileNotFoundError: si falta el checkpoint del clasificador de piezas.
        ValueError: si la partida ya terminó, si no se reconoció un tablero
            válido en la foto, o si ninguna jugada legal explica el cambio
            entre "antes" y "después" (ej. se movió más de una pieza, o la
            foto se sacó a mitad del movimiento).
    """
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")

    fen_antes = partida.fen
    tablero_antes = chess.Board(fen_antes)
    turno_despues = "b" if tablero_antes.turn == chess.WHITE else "w"

    imagen = capturar_foto_tablero()
    fen_despues = reconocer_tablero(imagen, turno=turno_despues)

    jugada_san = detectar_jugada(fen_antes, fen_despues)
    if jugada_san is None:
        raise ValueError(
            "No se pudo determinar qué jugada se hizo — la foto no coincide "
            "con ninguna jugada legal desde la posición anterior"
        )
    jugada_uci = tablero_antes.parse_san(jugada_san).uci()
    return mover(partida_id, jugada_uci)


def analisis_completo(partida_id: str, tiempo_limite: float = 0.3, rango: str = "Intermedio") -> dict:
    """Analiza con Stockfish cada jugada ya jugada de una partida (vista de aprendizaje, HU5/HU6).

    Reconstruye, jugada por jugada, todas las posiciones por las que pasó la
    partida desde `fen_inicial`, y le pide a `analizar_posicion` la evaluación
    de cada una. `analizar_posicion` siempre evalúa desde el punto de vista de
    quien tiene el turno en ese FEN — la posición "después" de una jugada le
    toca mover al rival, así que su evaluación queda en la perspectiva del
    rival, y hay que negarla para volver a la perspectiva de quien jugó, y así
    poder compararla contra lo que hubiera valido la mejor jugada (calculada
    en la posición "antes", ya en esa misma perspectiva).

    Abre un proceso de Stockfish por cada posición (N+1 para N jugadas), así
    que es lento para partidas largas — es una acción explícita del usuario
    ("analizar esta partida"), no algo que corra automáticamente, y
    `tiempo_limite` por defecto es más bajo que en el resto del motor para
    no tardar demasiado.

    El análisis retrospectivo siempre corre con `NIVEL_MAX` (fuerza máxima de
    Stockfish), nunca con `partida.nivel`. `partida.nivel` debilita cómo
    juega Stockfish EN VIVO contra el jugador (vía `Skill Level`) para que un
    principiante tenga chance — pero acá el motor no está jugando, está
    evaluando qué tan buena fue una jugada ya hecha, y esa evaluación tiene
    que ser la verdad objetiva de la posición. Si se usara `partida.nivel`,
    un análisis a nivel bajo puede devolver evaluaciones sin sentido (ej.
    "0 cp" en una posición con una dama de desventaja) porque Stockfish
    debilitado no ve tácticas simples — y esa evaluación rota alimenta
    `mejor_jugada_motor`, `variantes_candidatas`, la clasificación de calidad
    y la retroalimentación pedagógica (`explicar_jugada`), pudiendo terminar
    diciéndole a un jugador principiante justo lo contrario de lo que pasó.

    De paso, persiste la evaluación de cada jugada vía
    `RepositorioPartidas.actualizar_evaluacion_jugada` — es la única llamada a
    Stockfish que necesita `top_errores` en `/usuario/estadisticas` (HU14):
    como esta acción ya recalcula todo con Stockfish, guardarlo acá es gratis
    y evita que las estadísticas tengan que volver a llamar al motor.

    `rango` (RF20) adapta el texto de `explicacion` y de `consejo_tutor` al
    nivel del jugador ("Principiante", "Intermedio" o "Avanzado" — mismos
    valores que `UsuarioORM.rango_estimado`); lo decide la ruta HTTP según el
    usuario autenticado, acá solo se reenvía a `explicar_jugada` y
    `generar_resumen_partida`.

    Raises:
        KeyError: si no existe una partida con ese id.
    """
    partida = obtener_partida(partida_id)

    tablero = chess.Board(partida.fen_inicial)
    posiciones_fen = [tablero.fen()]
    for jugada in partida.tablero.move_stack:
        tablero.push(jugada)
        posiciones_fen.append(tablero.fen())

    analisis_por_posicion = [
        analizar_posicion(fen, NIVEL_MAX, tiempo_limite) for fen in posiciones_fen
    ]

    resultado = []
    for i, jugada_san in enumerate(partida.jugadas_san):
        antes = analisis_por_posicion[i]
        despues = analisis_por_posicion[i + 1]

        eval_resultante_cp = None if despues["evaluacion_cp"] is None else -despues["evaluacion_cp"]
        mate_resultante = None if despues["mate_en"] is None else -despues["mate_en"]

        numero_ply = i + 1
        _repositorio.actualizar_evaluacion_jugada(
            partida_id, numero_ply, eval_resultante_cp, mate_resultante,
            antes["evaluacion_cp"], antes["mate_en"],
        )

        cp_antes = antes["evaluacion_cp"] if antes["evaluacion_cp"] is not None else 0
        cp_despues = eval_resultante_cp if eval_resultante_cp is not None else 0
        perdida_cp = max(0, cp_antes - cp_despues)

        es_mejor = (antes["jugada"] == jugada_san) or (perdida_cp <= 10)
        calidad = clasificar_calidad_jugada(
            perdida_cp=perdida_cp,
            es_mejor_jugada=es_mejor,
            mate_en_antes=antes["mate_en"],
            mate_en_despues=mate_resultante,
        )
        principio, explicacion = explicar_jugada(
            fen_antes=posiciones_fen[i],
            jugada_san=jugada_san,
            fen_despues=posiciones_fen[i + 1],
            mejor_jugada_san=antes["jugada"],
            clasificacion=calidad,
            perdida_cp=perdida_cp,
            rango=rango,
        )
        prob_win = centipawns_a_probabilidad_victoria(eval_resultante_cp, mate_resultante)

        resultado.append({
            "numero_ply": numero_ply,
            "color": "blanco" if i % 2 == 0 else "negro",
            "jugada_san": jugada_san,
            "fen_antes": posiciones_fen[i],
            "fen_despues": posiciones_fen[i + 1],
            "evaluacion_cp": eval_resultante_cp,
            "mate_en": mate_resultante,
            "mejor_jugada_motor": antes["jugada"],
            "evaluacion_mejor_cp": antes["evaluacion_cp"],
            "mate_en_mejor": antes["mate_en"],
            "variantes_candidatas": antes["variantes_candidatas"],
            "calidad": calidad,
            "perdida_cp": perdida_cp,
            "probabilidad_victoria": prob_win,
            "principio_ajedrecistico": principio,
            "explicacion": explicacion,
        })

    resumen = generar_resumen_partida(resultado, rango=rango)
    return {"partida_id": partida_id, "jugadas": resultado, "resumen": resumen}
