"""Ciclo de vida de las partidas fuera de la jugada en sí: cerrar las que
quedan pendientes al crear una nueva, y barrer las que se abandonaron por
inactividad.

La Sala de Control crea una partida apenas se abre la pantalla (no hay botón
"iniciar"), así que si el facilitador la cierra sin jugar, o simplemente
navega a otra pantalla, esa partida queda `en_curso` para siempre si nadie la
cierra. Este módulo es el que decide qué hacer con esas partidas — nunca
borra ni toca una partida marcada `es_demostracion=True`, y usa
`MIN_JUGADAS_PARTIDA_VALIDA` (definida una sola vez en
`backend.servicios.calibracion`) para decidir entre borrar una partida vacía
o guardarla como `"abandonada"` porque ya tiene contenido útil.

Las funciones acá reciben el repositorio como parámetro (no importan
`servicio_partida._repositorio` directamente) para no crear un import
circular: `servicio_partida.py` es quien importa este módulo y le pasa su
propio repositorio, no al revés.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas
from backend.servicios.calibracion import MIN_JUGADAS_PARTIDA_VALIDA

logger = logging.getLogger(__name__)

HORAS_INACTIVIDAD_ABANDONO = 12
"""Con al menos una jugada del jugador, una partida `en_curso` sin novedad
por más de este tiempo se considera abandonada (o se borra, si tampoco llega
a `MIN_JUGADAS_PARTIDA_VALIDA`) — ver `limpiar_partidas_inactivas`."""

MINUTOS_PARTIDA_VACIA = 60
"""Una partida `en_curso` sin ninguna jugada del jugador se borra si pasó
este tiempo desde que se creó — nadie llegó siquiera a mover una vez."""


def _a_datetime_utc(valor: str) -> datetime:
    """Convierte un ISO 8601 (con o sin offset) a un `datetime` en UTC.

    Los que arma `Partida` en memoria siempre traen offset (`+00:00`); los
    que vuelven de una columna `TIMESTAMP` (sin zona) de Postgres, no —
    pero siempre se escribieron en UTC, así que un valor "naive" se asume
    UTC en vez de la zona local del proceso."""
    momento = datetime.fromisoformat(valor)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def _cerrar_o_borrar(partida: Partida, repositorio: RepositorioPartidas) -> None:
    """Decide entre borrar o marcar `"abandonada"` una partida `en_curso`
    que ya no hace falta conservar activa, según cuántas jugadas del jugador
    tiene."""
    if partida.jugadas_jugador < MIN_JUGADAS_PARTIDA_VALIDA:
        repositorio.eliminar(partida.id)
    else:
        partida.estado = "abandonada"
        repositorio.guardar(partida)


def cerrar_partidas_pendientes(repositorio: RepositorioPartidas, usuario_id: int) -> None:
    """Cierra las partidas `en_curso` que el usuario dejó pendientes, antes
    de crearle una nueva (llamado desde `servicio_partida.crear_partida`).

    Como se llama ANTES de crear la partida nueva, todas las `en_curso` que
    tenga el usuario en este momento son, por definición, "otras" partidas —
    no hace falta excluir ningún id a propósito. Nunca toca una partida en
    demostración (`es_demostracion=True`): esa sigue viva aunque el
    facilitador abra la Sala de Control de nuevo.
    """
    for partida in repositorio.listar_por_usuario(usuario_id):
        if partida.estado != "en_curso" or partida.es_demostracion:
            continue
        _cerrar_o_borrar(partida, repositorio)


def limpiar_partidas_inactivas(repositorio: RepositorioPartidas) -> None:
    """Barrido general (todos los usuarios) de partidas `en_curso` inactivas.

    Dos reglas, según si el jugador llegó a mover alguna vez:

    - Sin ninguna jugada del jugador: se borra si pasaron más de
      `MINUTOS_PARTIDA_VACIA` desde que se creó (`creada_en`) — se abrió la
      pantalla y nunca se jugó nada.
    - Con al menos una: se cierra (borrada o `"abandonada"`, según
      `MIN_JUGADAS_PARTIDA_VALIDA`) si pasaron más de
      `HORAS_INACTIVIDAD_ABANDONO` desde la última jugada (`actualizada_en`,
      o `creada_en` si por algún motivo no está seteada).

    Nunca toca una partida en demostración. Pensada para correr al arrancar
    el backend y cada vez que se pide `GET /partida/en-curso` — ambos
    lugares toleran que esta función falle sin romper el flujo del usuario.
    """
    ahora = datetime.now(timezone.utc)
    for partida in repositorio.listar():
        if partida.estado != "en_curso" or partida.es_demostracion:
            continue
        if partida.jugadas_jugador == 0:
            referencia = _a_datetime_utc(partida.creada_en)
            if ahora - referencia > timedelta(minutes=MINUTOS_PARTIDA_VACIA):
                repositorio.eliminar(partida.id)
            continue
        referencia = _a_datetime_utc(partida.actualizada_en or partida.creada_en)
        if ahora - referencia > timedelta(hours=HORAS_INACTIVIDAD_ABANDONO):
            _cerrar_o_borrar(partida, repositorio)


def partida_en_curso_de(repositorio: RepositorioPartidas, usuario_id: int) -> Partida | None:
    """Partida `en_curso` que el usuario puede retomar, o `None` si no hay
    ninguna (HU "retomar" — ver `GET /partida/en-curso`).

    Tres condiciones: `en_curso`, al menos una jugada del jugador (una recién
    creada sin jugar no es "retomar", es "empezar"), y no lleva más de
    `HORAS_INACTIVIDAD_ABANDONO` sin novedad — si las pasó, ya debería estar
    "abandonada" (normalmente `limpiar_partidas_inactivas`, llamada justo
    antes que esta función en la misma request, ya la cerró; este chequeo es
    una segunda red de seguridad, no la única).
    """
    candidatas = [
        partida
        for partida in repositorio.listar_por_usuario(usuario_id)
        if partida.estado == "en_curso" and not partida.es_demostracion and partida.jugadas_jugador >= 1
    ]
    if not candidatas:
        return None
    mas_reciente = candidatas[0]
    referencia = _a_datetime_utc(mas_reciente.actualizada_en or mas_reciente.creada_en)
    if datetime.now(timezone.utc) - referencia > timedelta(hours=HORAS_INACTIVIDAD_ABANDONO):
        return None
    return mas_reciente
