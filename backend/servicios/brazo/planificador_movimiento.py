"""Convierte una jugada de ajedrez en los pasos físicos que el brazo tiene que hacer (función pura: no toca ni el brazo ni la cámara).

Una jugada simple es un solo paso (origen → destino). Las demás necesitan más: la captura retira primero la pieza capturada al cementerio, el enroque mueve el rey
y la torre, la captura al paso retira un peón que no está en el destino, y la coronación retira el peón y pone una dama de reserva. Cada paso lleva el tipo de la pieza
que se agarra, para usar la apertura de pinza medida de esa pieza.

Los lugares que no son casillas se nombran con un prefijo: `cementerio:K` (la casilla K del cementerio) y `reserva:dama_blanca` / `reserva:dama_negra`.
"""
from __future__ import annotations

from dataclasses import dataclass

import chess

PREFIJO_CEMENTERIO = "cementerio:"
PREFIJO_RESERVA = "reserva:"
PIEZAS_INICIALES = 32


@dataclass(frozen=True)
class Paso:
    """Agarrar la pieza `pieza` (`"p"`, `"N"`…: la letra decide la apertura) de `origen` y soltarla en `destino`."""

    pieza: str
    origen: str
    destino: str


def piezas_retiradas(tablero: chess.Board) -> int:
    """Cuántas piezas hay ya en el cementerio: las que faltan en el tablero (32 − las que hay) más los peones coronados, que también se retiraron.

    Sale solo de la posición y sus jugadas, así no hay un contador que se pueda desincronizar. Una partida que arrancó de un FEN con menos piezas cuenta
    como si las faltantes ya estuvieran retiradas.
    """
    coronaciones = sum(1 for jugada in tablero.move_stack if jugada.promotion is not None)
    return max(0, PIEZAS_INICIALES - len(tablero.piece_map()) + coronaciones)


def cementerio(indice: int) -> str:
    return f"{PREFIJO_CEMENTERIO}{indice}"


def reserva_dama(color: chess.Color) -> str:
    return f"{PREFIJO_RESERVA}dama_{'blanca' if color == chess.WHITE else 'negra'}"


def planificar(tablero_antes: chess.Board, jugada: chess.Move) -> list[Paso]:
    """Los pasos para hacer `jugada` en el tablero físico, tal como estaba la posición antes de jugarla.

    Raises:
        ValueError: la jugada es una coronación que no es a dama (el brazo solo corona a dama), o no hay pieza en el origen.
    """
    pieza = tablero_antes.piece_at(jugada.from_square)
    if pieza is None:
        raise ValueError(f"No hay ninguna pieza en {chess.square_name(jugada.from_square)}")
    origen, destino = chess.square_name(jugada.from_square), chess.square_name(jugada.to_square)
    retiradas = piezas_retiradas(tablero_antes)
    pasos: list[Paso] = []
    if tablero_antes.is_en_passant(jugada):
        victima = chess.square(chess.square_file(jugada.to_square), chess.square_rank(jugada.from_square))
        pasos.append(Paso(tablero_antes.piece_at(victima).symbol(), chess.square_name(victima), cementerio(retiradas)))
        retiradas += 1
    elif tablero_antes.is_capture(jugada):
        capturada = tablero_antes.piece_at(jugada.to_square)
        pasos.append(Paso(capturada.symbol(), destino, cementerio(retiradas)))
        retiradas += 1
    if tablero_antes.is_castling(jugada):
        fila = chess.square_rank(jugada.from_square) + 1
        torre_origen, torre_destino = (f"h{fila}", f"f{fila}") if tablero_antes.is_kingside_castling(jugada) else (f"a{fila}", f"d{fila}")
        pasos += [Paso(pieza.symbol(), origen, destino), Paso("r", torre_origen, torre_destino)]
    elif jugada.promotion is not None:
        if jugada.promotion != chess.QUEEN:
            raise ValueError("El brazo solo corona a dama: la reserva es una dama por bando")
        pasos += [Paso(pieza.symbol(), origen, cementerio(retiradas)), Paso("q", reserva_dama(pieza.color), destino)]
    else:
        pasos.append(Paso(pieza.symbol(), origen, destino))
    return pasos


def forzar_dama(jugada: chess.Move) -> chess.Move:
    """La misma jugada pero coronando a dama si coronaba a otra pieza (regla de negocio: Turing solo corona a dama)."""
    if jugada.promotion is None or jugada.promotion == chess.QUEEN:
        return jugada
    return chess.Move(jugada.from_square, jugada.to_square, promotion=chess.QUEEN)
