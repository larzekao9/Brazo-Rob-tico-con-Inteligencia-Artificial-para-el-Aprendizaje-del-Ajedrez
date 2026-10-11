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

import logging
import time
from datetime import datetime, timezone

import chess

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas, crear_repositorio_partidas
from backend.servicios.brazo.servicio_brazo import ejecutar_respuesta_en_brazo
from backend.servicios.estrategias.fabrica_estrategias import TIPOS_SOPORTADOS, crear_estrategia_jugada
from backend.servicios.motor.motor_ajedrez import NIVEL_MAX, analizar_posicion, analizar_posiciones
import backend.servicios.partida.ciclo_vida as ciclo_vida
from backend.servicios.retroalimentacion.servicio_retroalimentacion import (
    analizar_jugada_en_tiempo_real,
    centipawns_a_probabilidad_victoria,
    clasificar_calidad_jugada,
    explicar_jugada,
    generar_resumen_partida,
)
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.deteccion_movimiento import detectar_jugada
from backend.servicios.vision.reconocimiento import reconocer_tablero

_repositorio: RepositorioPartidas = crear_repositorio_partidas()


CONTROL_TIEMPO_MIN_MS = 30_000
CONTROL_TIEMPO_MAX_MS = 2 * 60 * 60 * 1000


def _validar_control_tiempo(control_tiempo_ms: int) -> None:
    """El control de tiempo es 0 (sin reloj) o un valor razonable por lado: entre 30 s y 2 h."""
    if control_tiempo_ms != 0 and not CONTROL_TIEMPO_MIN_MS <= control_tiempo_ms <= CONTROL_TIEMPO_MAX_MS:
        raise ValueError(
            f"Control de tiempo inválido: {control_tiempo_ms} ms (0 = sin reloj, o entre "
            f"{CONTROL_TIEMPO_MIN_MS} y {CONTROL_TIEMPO_MAX_MS} ms por lado)"
        )


def crear_partida(
    nivel: int = 20,
    tipo_oponente: str = "motor",
    fen_inicial: str | None = None,
    usuario_id: int | None = None,
    control_tiempo_ms: int = 0,
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

    Antes de crear la partida, cierra las que el mismo usuario haya dejado
    pendientes (`ciclo_vida.cerrar_partidas_pendientes`) — la Sala de Control
    crea una partida apenas se abre la pantalla, sin botón "iniciar", así que
    sin este cierre cada apertura dejaría una partida `en_curso` más. Si
    `usuario_id` es `None` (partida sin dueño) no hay nada que cerrar.

    `control_tiempo_ms` es el tiempo de reloj de cada lado para toda la partida (`0` = sin reloj):
    queda guardado en la partida junto con lo que le resta a cada uno, así que al reanudarla el reloj
    sigue donde se quedó.

    Raises:
        ValueError: si `tipo_oponente` no es un tipo soportado todavía (ver
            `fabrica_estrategias.TIPOS_SOPORTADOS`), si `fen_inicial` no es
            un FEN válido o si `control_tiempo_ms` no es válido — todo se valida acá, al
            crear la partida, para no dejar que fallen recién en la primera jugada.
    """
    _validar_control_tiempo(control_tiempo_ms)
    if usuario_id is not None:
        ciclo_vida.cerrar_partidas_pendientes(_repositorio, usuario_id)
    if tipo_oponente not in TIPOS_SOPORTADOS:
        raise ValueError(
            f"Tipo de oponente '{tipo_oponente}' no soportado todavía "
            f"(disponibles: {sorted(TIPOS_SOPORTADOS)})"
        )
    if fen_inicial is None:
        partida = Partida(
            nivel=nivel, tipo_oponente=tipo_oponente, usuario_id=usuario_id, control_tiempo_ms=control_tiempo_ms
        )
    else:
        try:
            tablero = chess.Board(fen_inicial)
        except ValueError as error:
            raise ValueError(f"FEN inicial inválido: {fen_inicial}") from error
        if not tablero.piece_map():
            # Caso frecuente al probar la cámara/foto: el tablero físico está
            # vacío a propósito (sin piezas todavía) — mensaje aparte del de
            # "posición imposible" de abajo, porque acá no hay nada mal
            # reconocido: es que no hay piezas que reconocer.
            raise ValueError(
                "El tablero reconocido está vacío — no se detectó ninguna pieza en la foto. "
                "Armá el tablero con las piezas y volvé a intentar."
            )
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
            control_tiempo_ms=control_tiempo_ms,
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


def limpiar_partidas_inactivas() -> None:
    """Barrido de partidas `en_curso` abandonadas por inactividad (ver
    `ciclo_vida.limpiar_partidas_inactivas`) — se llama al arrancar el
    backend (`main.py`, tolerando errores) y en cada `GET /partida/en-curso`.
    """
    ciclo_vida.limpiar_partidas_inactivas(_repositorio)


def eliminar_partidas_de_usuario(usuario_id: int) -> int:
    """Borra todas las partidas (y sus jugadas) de un usuario; devuelve cuántas eran.

    Lo usa Gestión de Usuarios al eliminar una cuenta: las partidas no se pueden dejar huérfanas.
    """
    partidas = _repositorio.listar_por_usuario(usuario_id)
    for partida in partidas:
        _repositorio.eliminar(partida.id)
    return len(partidas)


def partida_en_curso_de(usuario_id: int) -> Partida | None:
    """Partida `en_curso` que el usuario puede retomar, o `None` (HU
    "retomar", ver `GET /partida/en-curso` y `ciclo_vida.partida_en_curso_de`).
    """
    return ciclo_vida.partida_en_curso_de(_repositorio, usuario_id)


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


def _san_a_uci(fen: str, jugada_san: str | None) -> str:
    """Pasa una jugada SAN ("Nf3") a casillas ("g1f3") en esa posición; `""` si no se puede.

    Solo sirve para dibujar flechas en el frontend, así que nunca debe romper un análisis.
    """
    if not jugada_san:
        return ""
    try:
        return chess.Board(fen).parse_san(jugada_san).uci()
    except ValueError:
        return ""


TIEMPO_ANALISIS_EN_VIVO = 0.3  # segundos por posición; igual que el análisis post-partida


def _calidad_de_la_jugada_humana(fen_antes: str, jugada_san: str, fen_despues: str) -> dict | None:
    """Califica la jugada que acaba de hacer el jugador (HU6): brillante, mejor, ..., blunder.

    Compara la posición antes y después de SU jugada, siempre con Stockfish a fuerza
    máxima (con un nivel bajo las evaluaciones no tienen sentido, ver `analisis_completo`),
    y con el mismo criterio de pérdida en centipeones que el análisis post-partida. Es
    un dato auxiliar: si el motor falla devuelve `None` y la jugada ya jugada no se pierde.
    """
    try:
        antes, despues = analizar_posiciones([fen_antes, fen_despues], NIVEL_MAX, TIEMPO_ANALISIS_EN_VIVO)
    except Exception:  # noqa: BLE001 — la jugada ya quedó guardada; esto es solo el indicador
        logging.getLogger(__name__).warning("No se pudo calificar la jugada en vivo", exc_info=True)
        return None

    # `despues` se evalúa desde el bando que mueve ahora (el rival): se invierte el signo.
    eval_resultante = None if despues["evaluacion_cp"] is None else -despues["evaluacion_cp"]
    mate_resultante = None if despues["mate_en"] is None else -despues["mate_en"]
    return analizar_jugada_en_tiempo_real(
        fen_antes=fen_antes,
        jugada_san=jugada_san,
        fen_despues=fen_despues,
        evaluacion_antes_cp=antes["evaluacion_cp"] if antes["evaluacion_cp"] is not None else 0,
        evaluacion_despues_cp=eval_resultante if eval_resultante is not None else 0,
        mejor_jugada_san=antes["jugada"],
        mate_en_antes=antes["mate_en"],
        mate_en_despues=mate_resultante,
    )


def actualizar_reloj(
    partida_id: str,
    blancas_ms: int | None = None,
    negras_ms: int | None = None,
    control_tiempo_ms: int | None = None,
) -> Partida:
    """Guarda lo que le queda a cada lado en el reloj, o cambia el control de tiempo antes de empezar.

    La pantalla lo llama cada pocos segundos mientras corre el reloj y al cerrar la pestaña, para que al
    reanudar la partida el reloj siga donde se quedó (y no corra mientras el jugador estuvo fuera). El
    tiempo solo puede bajar: un valor mayor al que ya había se ignora.

    `control_tiempo_ms` solo se acepta mientras no se jugó ninguna jugada, y reinicia ambos relojes.

    Raises:
        KeyError: si no existe la partida.
        ValueError: si ya terminó, si la partida no tiene reloj o si el control de tiempo es inválido o
            se quiere cambiar con la partida empezada.
    """
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")
    if control_tiempo_ms is not None:
        if partida.tablero.move_stack:
            raise ValueError("El control de tiempo no se puede cambiar con la partida empezada")
        _validar_control_tiempo(control_tiempo_ms)
        partida.control_tiempo_ms = control_tiempo_ms
        partida.tiempo_blancas_ms = None
        partida.tiempo_negras_ms = None
    elif partida.control_tiempo_ms == 0:
        raise ValueError("La partida no tiene reloj")
    if partida.control_tiempo_ms:
        if blancas_ms is not None:
            partida.tiempo_blancas_ms = max(0, min(int(blancas_ms), partida.restante_blancas_ms))
        if negras_ms is not None:
            partida.tiempo_negras_ms = max(0, min(int(negras_ms), partida.restante_negras_ms))
    _repositorio.guardar(partida)
    return partida


def terminar_por_tiempo(partida_id: str, lado: str) -> Partida:
    """Termina la partida porque al `lado` (`"blancas"` o `"negras"`) se le acabó el tiempo del reloj.

    Pierde ese lado: `"0-1"` si fueron las blancas (el humano) y `"1-0"` si fueron las negras. El servidor
    no lleva reloj (lo hace la pantalla), así que confía en lo que le informa el dueño de la partida; es
    equivalente a abandonar, que ya era posible. Una partida terminada así cuenta como terminada para el
    historial, las estadísticas y la calibración del nivel.

    Raises:
        KeyError: si no existe la partida.
        ValueError: si ya terminó, si `lado` es inválido o si todavía no se jugó ninguna jugada.
    """
    if lado not in ("blancas", "negras"):
        raise ValueError(f"Lado inválido: {lado!r} (debe ser 'blancas' o 'negras')")
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")
    if not partida.tablero.move_stack:
        raise ValueError("Una partida sin jugadas no puede terminar por tiempo")
    partida.resultado_por_tiempo = "0-1" if lado == "blancas" else "1-0"
    if partida.control_tiempo_ms:
        if lado == "blancas":
            partida.tiempo_blancas_ms = 0
        else:
            partida.tiempo_negras_ms = 0
    partida.estado = "terminada"
    partida.actualizada_en = datetime.now(timezone.utc).isoformat()
    _repositorio.guardar(partida)
    return partida


def mover(
    partida_id: str,
    jugada_uci: str,
    tiempo_jugada_ms: int | None = None,
    reloj_blancas_ms: int | None = None,
) -> dict:
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

    Si la partida sigue en curso, la jugada de la estrategia (nunca la del
    humano — esa ya se jugó a mano sobre el tablero físico real) también se
    manda al brazo vía `ejecutar_respuesta_en_brazo` (HU9) — no-op si
    `partida.usa_brazo` es `False`. Un fallo físico del brazo no aborta esta
    función ni deja la jugada digital sin aplicar: queda expuesto en
    `error_brazo` en el resultado.

    También actualiza el ciclo de vida de la partida (HU sala de control):
    fija `iniciada_en` en la primera llamada (primera jugada del humano),
    pisa `actualizada_en` en cada llamada, y pasa `estado` a `"terminada"`
    si esta jugada termina la partida.

    Tiempos: `tiempo_jugada_ms` es cuánto tardó el humano en decidir esta jugada (lo mide la pantalla) y
    `reloj_blancas_ms` lo que le queda en el reloj; ambos son opcionales. El tiempo de la respuesta del
    rival lo mide acá el servidor (cuánto tardó en decidirla) y se descuenta de su reloj. Cada jugada
    deja su tiempo en `partida.tiempos_jugadas_ms` y el resultado trae el estado del reloj en `reloj`.

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
    jugada_humano_san = tablero_intento.san(jugada_humano)
    tablero_intento.push(jugada_humano)
    fen_despues_humano = tablero_intento.fen()
    jugadas_a_registrar = [
        (len(tablero_intento.move_stack), fen_antes_humano, jugada_humano.uci(), "jugador")
    ]

    jugada_motor_san = None
    tiempo_rival_ms: int | None = None
    error_brazo: str | None = None
    if not tablero_intento.is_game_over():
        estrategia = crear_estrategia_jugada(partida.tipo_oponente, nivel=partida.nivel)
        fen_antes_motor = tablero_intento.fen()
        inicio_decision = time.perf_counter()
        jugada_motor_san = estrategia.decidir_jugada(fen_antes_motor)
        tiempo_rival_ms = int((time.perf_counter() - inicio_decision) * 1000)
        tablero_antes_motor = tablero_intento.copy()
        jugada_motor_move = tablero_intento.parse_san(jugada_motor_san)
        tablero_intento.push(jugada_motor_move)
        jugadas_a_registrar.append((
            len(tablero_intento.move_stack),
            fen_antes_motor,
            jugada_motor_move.uci(),
            partida.tipo_oponente,
        ))
        error_brazo = ejecutar_respuesta_en_brazo(partida, tablero_antes_motor, jugada_motor_move)

    ahora = datetime.now(timezone.utc).isoformat()
    if partida.iniciada_en is None:
        partida.iniciada_en = ahora
    partida.actualizada_en = ahora
    # Tiempos: se alinean con las jugadas ya jugadas (partidas anteriores a esta columna) y se suman las nuevas.
    jugadas_previas = len(partida.tablero.move_stack)
    partida.tiempos_jugadas_ms = (partida.tiempos_jugadas_ms + [None] * jugadas_previas)[:jugadas_previas]
    partida.tiempos_jugadas_ms.append(None if tiempo_jugada_ms is None else max(0, int(tiempo_jugada_ms)))
    if tiempo_rival_ms is not None:
        partida.tiempos_jugadas_ms.append(tiempo_rival_ms)
    if partida.control_tiempo_ms:
        if reloj_blancas_ms is not None:
            partida.tiempo_blancas_ms = max(0, min(int(reloj_blancas_ms), partida.restante_blancas_ms))
        if tiempo_rival_ms is not None:
            partida.tiempo_negras_ms = max(0, partida.restante_negras_ms - tiempo_rival_ms)
    partida.tablero = tablero_intento
    if partida.terminada:
        partida.estado = "terminada"
    _repositorio.guardar(partida)
    for numero, fen_antes, movimiento, decidido_por in jugadas_a_registrar:
        _repositorio.registrar_jugada(partida.id, numero, fen_antes, movimiento, decidido_por)

    # Analizar la posición resultante de la jugada humana para obtener variantes candidatas
    # y retroalimentación pedagógica en vivo (HU6)
    variantes_candidatas: list[dict] = []
    retroalimentacion_en_vivo: dict | None = None
    if not partida.terminada and jugada_motor_san is not None:
        analisis = analizar_posicion(partida.fen, NIVEL_MAX, TIEMPO_ANALISIS_EN_VIVO)  # fuerza máxima: el nivel de la partida solo regula al rival
        variantes_candidatas = analisis.get("variantes_candidatas", [])

        retroalimentacion_en_vivo = _calidad_de_la_jugada_humana(
            fen_antes_humano, jugada_humano_san, fen_despues_humano
        )

    return {
        "fen": partida.fen,
        "fen_tras_jugada": fen_despues_humano,
        "jugada_motor": jugada_motor_san,
        "terminada": partida.terminada,
        "resultado": partida.resultado,
        "jugadas": partida.jugadas_san,
        "variantes_candidatas": variantes_candidatas,
        "retroalimentacion_en_vivo": retroalimentacion_en_vivo,
        "error_brazo": error_brazo,
        "reloj": _estado_del_reloj(partida),
    }


def _estado_del_reloj(partida: Partida) -> dict | None:
    """Lo que le queda a cada lado, o `None` si la partida no tiene reloj."""
    if not partida.control_tiempo_ms:
        return None
    return {
        "control_tiempo_ms": partida.control_tiempo_ms,
        "blancas_ms": partida.restante_blancas_ms,
        "negras_ms": partida.restante_negras_ms,
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


def _resumen_de_tiempos(partida: Partida) -> dict:
    """Cuánto duró la partida y cuánto tardó el estudiante por jugada (solo jugadas medidas)."""
    del_estudiante = [t for t in partida.tiempos_jugadas_ms[::2] if t is not None]
    return {
        "control_tiempo_ms": partida.control_tiempo_ms,
        "duracion_ms": partida.duracion_ms or None,
        "tiempo_medio_jugador_ms": round(sum(del_estudiante) / len(del_estudiante)) if del_estudiante else None,
    }


def analisis_completo(partida_id: str, tiempo_limite: float = 0.3, rango: str = "Intermedio") -> dict:
    """Analiza con Stockfish cada jugada ya jugada de una partida (vista de aprendizaje, HU5/HU6).

    Reconstruye, jugada por jugada, todas las posiciones por las que pasó la
    partida desde `fen_inicial`, y le pide a `analizar_posiciones` la evaluación
    de cada una. El análisis siempre evalúa desde el punto de vista de
    quien tiene el turno en ese FEN — la posición "después" de una jugada le
    toca mover al rival, así que su evaluación queda en la perspectiva del
    rival, y hay que negarla para volver a la perspectiva de quien jugó, y así
    poder compararla contra lo que hubiera valido la mejor jugada (calculada
    en la posición "antes", ya en esa misma perspectiva).

    Analiza las N+1 posiciones de una partida de N jugadas con
    `analizar_posiciones`: abre unos pocos procesos de Stockfish una sola vez
    y los reparte en paralelo, en vez de abrir uno por posición. Aun así
    cuesta `tiempo_limite` por posición dividido entre los motores, y es una
    acción explícita del usuario ("analizar esta partida") o el cierre de una
    partida terminada; `tiempo_limite` por defecto es más bajo que en el resto
    del motor para no tardar demasiado. Un error del motor se propaga tal cual.

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

    analisis_por_posicion = analizar_posiciones(posiciones_fen, NIVEL_MAX, tiempo_limite)

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
        # El humano siempre juega primero (blancas): sus jugadas son las de índice par.
        es_jugador = i % 2 == 0
        principio, explicacion = explicar_jugada(
            fen_antes=posiciones_fen[i],
            jugada_san=jugada_san,
            fen_despues=posiciones_fen[i + 1],
            mejor_jugada_san=antes["jugada"],
            clasificacion=calidad,
            perdida_cp=perdida_cp,
            rango=rango,
            es_jugador=es_jugador,
        )
        prob_win = centipawns_a_probabilidad_victoria(eval_resultante_cp, mate_resultante)

        resultado.append({
            "numero_ply": numero_ply,
            "color": "blanco" if i % 2 == 0 else "negro",
            "quien": "jugador" if es_jugador else "contraparte",
            "jugada_san": jugada_san,
            "jugada_uci": _san_a_uci(posiciones_fen[i], jugada_san),
            "mejor_jugada_uci": _san_a_uci(posiciones_fen[i], antes["jugada"]),
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
            "tiempo_ms": partida.tiempos_jugadas_ms[i] if i < len(partida.tiempos_jugadas_ms) else None,
        })

    resumen = generar_resumen_partida(resultado, rango=rango)
    resumen["nivel_partida"] = partida.nivel
    resumen.update(_resumen_de_tiempos(partida))
    return {"partida_id": partida_id, "jugadas": resultado, "resumen": resumen}
