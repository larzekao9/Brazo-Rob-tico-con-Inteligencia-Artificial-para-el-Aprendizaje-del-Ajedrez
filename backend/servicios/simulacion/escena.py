"""Escena 3D simplificada de un tablero de ajedrez en PyBullet."""
from __future__ import annotations

import math
from pathlib import Path

import chess
import pybullet as p
import pybullet_data

TAMANO_CASILLA = 1.0
ALTO_CASILLA = 0.05

COLOR_CLARO = [0.85, 0.85, 0.75, 1.0]
COLOR_OSCURO = [0.35, 0.25, 0.15, 1.0]
COLOR_ORIGEN = [1.0, 1.0, 0.0, 1.0]
COLOR_DESTINO = [0.0, 1.0, 0.0, 1.0]

ASSETS_PIEZAS_DIR = Path(__file__).parent / "assets" / "piezas"
CARPETA_POR_COLOR = {chess.WHITE: "claro", chess.BLACK: "oscuro"}
ARCHIVO_POR_TIPO_PIEZA = {
    chess.KING: "rey",
    chess.QUEEN: "reina",
    chess.BISHOP: "alfil",
    chess.KNIGHT: "caballo",
    chess.ROOK: "torre",
    chess.PAWN: "peon",
}

# Las piezas vienen en metros reales de un set Staunton (peon=0.065 hasta rey=0.12)
# mientras que TAMANO_CASILLA=1.0 es una unidad abstracta del tablero, no un metro.
# La pieza mas ancha en su base (rey, ~0.045 de diametro) debe ocupar entre 70% y 80%
# del ancho de su casilla para verse proporcionada; 16x deja al rey en ~72%.
ESCALA_PIEZA = 16.0

# Los .obj fueron exportados desde Blender con la convencion Y-arriba (el mesh
# tiene su altura en el eje Y, base en Y=0), pero el mundo de PyBullet usa Z-arriba.
# Esta es la orientacion del visual shape (no del body) que rota +90 grados sobre
# X para que la altura de la malla quede alineada con el eje Z del mundo.
_MEDIO_ANGULO = math.pi / 4
ROTACION_MALLA_Y_ARRIBA_A_Z_ARRIBA = (
    math.sin(_MEDIO_ANGULO),
    0.0,
    0.0,
    math.cos(_MEDIO_ANGULO),
)


def cargar_formas_visuales_piezas(client_id: int) -> dict[tuple[int, bool], int]:
    """Carga los 12 mallas .obj de piezas (6 tipos x 2 colores) como visual shapes.

    Pensada para llamarse una sola vez por conexión y reusar el dict devuelto
    en cada `sincronizar_piezas` posterior, en vez de releer los .obj del
    disco por cada jugada.
    """
    formas: dict[tuple[int, bool], int] = {}
    for tipo_pieza, nombre_archivo in ARCHIVO_POR_TIPO_PIEZA.items():
        for color, carpeta in CARPETA_POR_COLOR.items():
            ruta_obj = ASSETS_PIEZAS_DIR / carpeta / f"{nombre_archivo}.obj"
            formas[(tipo_pieza, color)] = p.createVisualShape(
                p.GEOM_MESH,
                fileName=str(ruta_obj),
                meshScale=[ESCALA_PIEZA] * 3,
                visualFrameOrientation=ROTACION_MALLA_Y_ARRIBA_A_Z_ARRIBA,
                physicsClientId=client_id,
            )
    return formas


def _posicion_casilla(columna: int, fila: int, z: float) -> list[float]:
    return [
        (columna - 3.5) * TAMANO_CASILLA,
        (fila - 3.5) * TAMANO_CASILLA,
        z,
    ]


def _crear_piezas_desde_tablero(
    client_id: int,
    tablero: chess.Board,
    formas_visuales: dict[tuple[int, bool], int],
) -> dict[str, int]:
    piezas: dict[str, int] = {}
    for casilla_idx, pieza in tablero.piece_map().items():
        columna = chess.square_file(casilla_idx)
        fila = chess.square_rank(casilla_idx)
        body_id = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=formas_visuales[(pieza.piece_type, pieza.color)],
            basePosition=_posicion_casilla(columna, fila, ALTO_CASILLA),
            physicsClientId=client_id,
        )
        piezas[chess.square_name(casilla_idx)] = body_id
    return piezas


def _crear_piezas_posicion_inicial(client_id: int) -> dict[str, int]:
    formas_visuales = cargar_formas_visuales_piezas(client_id)
    return _crear_piezas_desde_tablero(client_id, chess.Board(), formas_visuales)


def crear_escena(modo_gui: bool = False) -> tuple[int, dict[str, int], dict[str, int]]:
    """Crea una escena de PyBullet con un tablero de ajedrez 8x8 y sus piezas.

    Args:
        modo_gui: si es True abre una ventana (p.GUI), si no corre headless
            (p.DIRECT), útil para tests y ejecución sin pantalla.

    Returns:
        Tupla con el client_id de la conexión a PyBullet, un dict que mapea
        notación algebraica (ej. "e4") al body_id de esa casilla, y un dict
        que mapea notación algebraica al body_id de la pieza ubicada ahí en
        la posición inicial estándar (solo para las 32 casillas ocupadas).
    """
    client_id = p.connect(p.GUI if modo_gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client_id)
    p.loadURDF("plane.urdf", physicsClientId=client_id)

    casillas: dict[str, int] = {}
    forma_colision = p.createCollisionShape(
        p.GEOM_BOX,
        halfExtents=[TAMANO_CASILLA / 2, TAMANO_CASILLA / 2, ALTO_CASILLA / 2],
        physicsClientId=client_id,
    )

    for fila in range(8):
        for columna in range(8):
            casilla = chess.square_name(chess.square(columna, fila))
            body_id = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=forma_colision,
                basePosition=_posicion_casilla(columna, fila, ALTO_CASILLA / 2),
                physicsClientId=client_id,
            )
            color = COLOR_CLARO if (fila + columna) % 2 == 0 else COLOR_OSCURO
            p.changeVisualShape(body_id, -1, rgbaColor=color, physicsClientId=client_id)
            casillas[casilla] = body_id

    piezas = _crear_piezas_posicion_inicial(client_id)

    return client_id, casillas, piezas


def resaltar_jugada(casillas: dict[str, int], desde: str, hasta: str, client_id: int) -> None:
    """Resalta visualmente la casilla de origen y destino de una jugada.

    Args:
        casillas: dict notación algebraica -> body_id, devuelto por crear_escena.
        desde: casilla de origen (ej. "e2").
        hasta: casilla de destino (ej. "e4").
        client_id: client_id de la conexión a PyBullet.
    """
    p.changeVisualShape(casillas[desde], -1, rgbaColor=COLOR_ORIGEN, physicsClientId=client_id)
    p.changeVisualShape(casillas[hasta], -1, rgbaColor=COLOR_DESTINO, physicsClientId=client_id)


def sincronizar_piezas(
    client_id: int,
    piezas_actuales: dict[str, int],
    tablero: chess.Board,
    formas_visuales: dict[tuple[int, bool], int],
) -> dict[str, int]:
    """Reemplaza todas las piezas de la escena por las que corresponden a `tablero`.

    Borra los body_id de `piezas_actuales` y crea las piezas desde cero según
    `tablero.piece_map()`, sin diff pieza por pieza — pensada para llamarse una
    vez por jugada, no por frame.

    Args:
        client_id: client_id de la conexión a PyBullet.
        piezas_actuales: dict notación algebraica -> body_id, de la escena tal
            como está antes de sincronizar (ej. lo que devolvió `crear_escena`
            o una llamada anterior a esta misma función).
        tablero: posición a reflejar en la escena.
        formas_visuales: dict devuelto por `cargar_formas_visuales_piezas`,
            reusado para no releer los .obj de disco en cada jugada.

    Returns:
        Nuevo dict notación algebraica -> body_id para la posición dada.
    """
    for body_id in piezas_actuales.values():
        p.removeBody(body_id, physicsClientId=client_id)
    return _crear_piezas_desde_tablero(client_id, tablero, formas_visuales)


def cerrar_escena(client_id: int) -> None:
    """Cierra la conexión a PyBullet asociada al client_id dado."""
    p.disconnect(client_id)
