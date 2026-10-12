"""Servicio de salas (humano vs humano).

Funciones pequeñas, probables sin cámara ni modelo. No hay estrategia de IA:
los dos jugadores mueven sus propias piezas. Stockfish solo se usa en el
análisis posterior (Fase 2).
"""
from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone

import chess

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas, crear_repositorio_partidas


def _a_datetime_utc(valor: str) -> datetime:
    """Convierte un ISO 8601 (con o sin offset) a un `datetime` en UTC.

    Los que arma `Partida` en memoria siempre traen offset (`+00:00`); los
    que vuelven de una columna `TIMESTAMP` (sin zona) de Postgres, no —
    pero siempre se escribieron en UTC, así que un valor "naive" se asume
    UTC en vez de la zona local del proceso.
    """
    momento = datetime.fromisoformat(valor)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)

_repositorio: RepositorioPartidas = crear_repositorio_partidas()

# Alfabeto sin ambiguos para códigos de sala (sin 0, O, 1, I, L)
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_LONGITUD_CODIGO = 6

# Locks por partida para evitar condiciones de carrera en mover_humano
_locks_partida: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _lock_para(partida_id: str) -> threading.Lock:
    """Obtiene (o crea) el lock para una partida."""
    with _locks_lock:
        if partida_id not in _locks_partida:
            _locks_partida[partida_id] = threading.Lock()
        return _locks_partida[partida_id]


def _generar_codigo() -> str:
    """Genera un código de 6 caracteres único."""
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_LONGITUD_CODIGO))


def _rol_desde_asiento(partida: Partida, usuario_id: int) -> str:
    """Determina el rol del usuario en la sala."""
    if partida.usuario_blancas_id == usuario_id:
        return "blancas"
    if partida.usuario_negras_id == usuario_id:
        return "negras"
    return "espectador"


def _color_turno_a_str(turno: chess.Color) -> str:
    return "blancas" if turno == chess.WHITE else "negras"


def _calcular_version(partida: Partida) -> int:
    """Versión determinista: plies * 10 + índice del estado.

    Índices: esperando=0, en_curso=1, terminada=2, abandonada=3.
    Evita `hash(str)` que cambia entre procesos y puede colisionar.
    """
    estado_idx = {"esperando": 0, "en_curso": 1, "terminada": 2, "abandonada": 3}.get(partida.estado, 0)
    return len(partida.tablero.move_stack) * 10 + estado_idx


def crear_sala(usuario_id: int, color: str) -> Partida:
    """Crea una sala `esperando` con código único.

    Args:
        usuario_id: Quién crea la sala.
        color: "blancas", "negras" o "aleatorio".

    Cancela (elimina) las salas `esperando` anteriores del mismo creador: solo
    puede tener una sala abierta esperando rival.

    Returns:
        La Partida creada con `tipo_oponente="humano"` y `estado="esperando"`.

    Raises:
        RuntimeError: si no se pudo generar un código único tras 10 intentos.
    """
    if color == "aleatorio":
        color = secrets.choice(["blancas", "negras"])

    for previa in _repositorio.listar_por_usuario(usuario_id):
        if previa.tipo_oponente == "humano" and previa.estado == "esperando":
            _repositorio.eliminar(previa.id)

    codigo = _generar_codigo()
    # Asegurar unicidad (muy improbable colisión, pero por si acaso)
    for _ in range(10):
        try:
            # Verificar si ya existe
            _repositorio.obtener_por_codigo(codigo)
            codigo = _generar_codigo()
        except KeyError:
            break
    else:
        # Se agotaron los 10 intentos sin encontrar código libre
        raise RuntimeError("No se pudo generar un código de sala único")

    ahora = datetime.now(timezone.utc).isoformat()
    partida = Partida(
        nivel=0,
        tipo_oponente="humano",
        estado="esperando",
        fen_inicial=chess.STARTING_FEN,
        usuario_id=usuario_id,
        control_tiempo_ms=0,
        codigo_sala=codigo,
        usuario_blancas_id=usuario_id if color == "blancas" else None,
        usuario_negras_id=usuario_id if color == "negras" else None,
    )
    _repositorio.guardar(partida)
    return partida


def unirse(codigo: str, usuario_id: int) -> Partida:
    """Une al usuario a la sala si hay asiento libre.

    - Si el asiento del color elegido está libre → lo ocupa y la sala pasa a `en_curso`.
    - Si el usuario ya está sentado → idempotente (no cambia nada).
    - Si la sala está llena → devuelve la sala con `rol="espectador"` (no error).
    - Si la sala ya terminó → devuelve la sala (el análisis se pide aparte).

    Raises:
        KeyError: si el código no existe.
    """
    partida = _repositorio.obtener_por_codigo(codigo)

    # Lock por partida para evitar carrera al ocupar asiento
    with _lock_para(partida.id):
        # Releer bajo el lock
        partida = _repositorio.obtener_por_codigo(codigo)

        # Si el usuario ya está en la sala, no hace nada (idempotente)
        if partida.usuario_blancas_id == usuario_id or partida.usuario_negras_id == usuario_id:
            return partida

        # Si la sala está esperando y hay asiento libre
        if partida.estado == "esperando":
            if partida.usuario_blancas_id is None:
                partida.usuario_blancas_id = usuario_id
            elif partida.usuario_negras_id is None:
                partida.usuario_negras_id = usuario_id
            else:
                # No debería pasar en estado "esperando"
                pass

            # Si ahora los dos asientos están ocupados, pasa a en_curso
            if partida.usuario_blancas_id is not None and partida.usuario_negras_id is not None:
                partida.estado = "en_curso"
                partida.iniciada_en = datetime.now(timezone.utc).isoformat()

            _repositorio.guardar(partida)
            return partida

        # Sala llena o en curso/terminada -> espectador
        return partida


def obtener_estado(codigo: str, usuario_id: int) -> Partida:
    """Devuelve el estado actual de la sala con el rol de quien consulta.

    Usado para polling desde el frontend.
    """
    partida = _repositorio.obtener_por_codigo(codigo)
    return partida


def jugadas_legales_sala(codigo: str, casilla: str) -> list[str]:
    """Devuelve las casillas destino legales para la pieza en `casilla`.

    Igual que `/partida/.../jugadas-legales` pero por código de sala.
    """
    partida = _repositorio.obtener_por_codigo(codigo)
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


def mover_humano(codigo: str, usuario_id: int, jugada_uci: str) -> Partida:
    """Aplica la jugada del humano en la sala.

    - Solo el jugador al que le toca puede mover.
    - Valida que la jugada sea legal.
    - Guarda la jugada y actualiza `actualizada_en`.
    - Detecta fin de partida (mate, tablas, abandono).
    - Usa lock por partida para evitar condiciones de carrera.

    Raises:
        KeyError: si el código no existe.
        ValueError: si jugada ilegal, sala `esperando`, o partida ya terminada.
        PermissionError: si el usuario es espectador o no es su turno.
    """
    partida = _repositorio.obtener_por_codigo(codigo)

    if partida.tipo_oponente != "humano":
        raise ValueError("Esta función solo es para salas humano vs humano")

    if partida.estado == "esperando":
        raise ValueError("La sala está esperando al segundo jugador")
    if partida.terminada or partida.estado in ("terminada", "abandonada"):
        raise ValueError("La partida ya terminó")

    # Determinar el color del usuario
    rol = _rol_desde_asiento(partida, usuario_id)
    if rol == "espectador":
        raise PermissionError("Los espectadores no pueden mover")

    turno_actual = _color_turno_a_str(partida.tablero.turn)
    if rol != turno_actual:
        raise PermissionError("No es tu turno")

    # Validar y aplicar jugada
    try:
        jugada = partida.tablero.parse_uci(jugada_uci)
    except ValueError as error:
        raise ValueError(f"Jugada inválida: {jugada_uci}") from error

    if jugada not in partida.tablero.legal_moves:
        raise ValueError(f"Jugada ilegal: {jugada_uci}")

    # Lock por partida para evitar condiciones de carrera
    with _lock_para(partida.id):
        # Re-verificar estado bajo el lock
        partida = _repositorio.obtener_por_codigo(codigo)
        if partida.terminada or partida.estado in ("terminada", "abandonada"):
            raise ValueError("La partida ya terminó")

        turno_actual = _color_turno_a_str(partida.tablero.turn)
        rol = _rol_desde_asiento(partida, usuario_id)
        if rol == "espectador" or rol != turno_actual:
            raise PermissionError("No es tu turno")

        # Aplicar jugada
        fen_antes = partida.tablero.fen()
        jugada_san = partida.tablero.san(jugada)
        partida.tablero.push(jugada)
        fen_despues = partida.tablero.fen()

        # Actualizar timestamps
        ahora = datetime.now(timezone.utc).isoformat()
        if partida.iniciada_en is None:
            partida.iniciada_en = ahora
        partida.actualizada_en = ahora

        # Detectar fin
        if partida.tablero.is_game_over():
            partida.estado = "terminada"
            # resultado y motivo_fin se leen de tablero.result() y tablero.outcome()

        _repositorio.guardar(partida)
        # Registrar jugada en tabla jugada
        _repositorio.registrar_jugada(
            partida.id,
            len(partida.tablero.move_stack),
            fen_antes,
            jugada.uci(),
            "jugador",
        )

    return partida


def abandonar(codigo: str, usuario_id: int) -> Partida:
    """Abandona la sala: gana el otro jugador.

    Raises:
        KeyError: si el código no existe.
        PermissionError: si el usuario es espectador.
        ValueError: si la partida ya terminó o está esperando segundo jugador.
    """
    partida = _repositorio.obtener_por_codigo(codigo)

    if partida.tipo_oponente != "humano":
        raise ValueError("Esta función solo es para salas humano vs humano")

    if partida.terminada or partida.estado in ("terminada", "abandonada"):
        raise ValueError("La partida ya terminó")

    if partida.estado == "esperando":
        raise ValueError(
            f"No se puede abandonar una sala que espera al segundo jugador: cancelala con DELETE /sala/{codigo}"
        )

    rol = _rol_desde_asiento(partida, usuario_id)
    if rol == "espectador":
        raise PermissionError("Los espectadores no pueden abandonar")

    # El otro jugador gana
    if rol == "blancas":
        partida.resultado_por_tiempo = "0-1"  # negras ganan
    else:
        partida.resultado_por_tiempo = "1-0"  # blancas ganan

    # Abandono manual = partida terminada, NO "abandonada" (que es por inactividad)
    partida.estado = "terminada"
    partida.actualizada_en = datetime.now(timezone.utc).isoformat()
    _repositorio.guardar(partida)
    return partida


def cancelar_sala(codigo: str, usuario_id: int) -> None:
    """Cancela (elimina) una sala `esperando`: solo la puede cancelar su creador.

    Raises:
        KeyError: si el código no existe.
        PermissionError: si el usuario no es el creador.
        ValueError: si la sala ya no está `esperando` (ya tiene rival o terminó).
    """
    partida = _repositorio.obtener_por_codigo(codigo)
    if partida.tipo_oponente != "humano":
        raise ValueError("Esta función solo es para salas humano vs humano")
    if partida.usuario_id != usuario_id:
        raise PermissionError("Solo el creador puede cancelar la sala")
    with _lock_para(partida.id):
        partida = _repositorio.obtener_por_codigo(codigo)
        if partida.estado != "esperando":
            raise ValueError("Solo se puede cancelar una sala que está esperando rival")
        _repositorio.eliminar(partida.id)


def analisis_sala(codigo: str, rango: str = "Intermedio") -> dict:
    """Análisis general con Stockfish de una sala terminada (contrato de PLAN_MULTIJUGADOR.md §6.3).

    Delega en `analisis_partida_sala.construir_analisis` (perspectiva neutra, sin persistir
    evaluaciones, con caché en memoria). No incluye `codigo` ni nombres: los agrega la ruta.

    Raises:
        KeyError: si el código no existe.
        ValueError: si la partida no terminó.
    """
    from backend.servicios.sala.analisis_partida_sala import construir_analisis

    partida = _repositorio.obtener_por_codigo(codigo)

    if not partida.terminada and partida.estado not in ("terminada", "abandonada"):
        raise ValueError("La partida no ha terminado")

    return construir_analisis(partida, rango=rango)


def sala_activa_de(usuario_id: int) -> Partida | None:
    """Devuelve la sala `esperando` o `en_curso` más reciente del usuario, o `None`.

    Usado para la tarjeta de Inicio.
    """
    salas = _repositorio.listar_por_participante(usuario_id)
    for partida in salas:
        if partida.tipo_oponente == "humano" and partida.estado in ("esperando", "en_curso"):
            return partida
    return None


from backend.servicios.sala.limpieza_salas import (  # noqa: E402,F401
    HORAS_SALA_INACTIVA,
    MINUTOS_SALA_SIN_JUGADAS,
    MINUTOS_SALA_VACIA,
    limpiar_salas_inactivas,
)
