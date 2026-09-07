"""Escena 3D simplificada de un tablero de ajedrez en PyBullet."""
from __future__ import annotations

import chess
import pybullet as p
import pybullet_data

TAMANO_CASILLA = 1.0
ALTO_CASILLA = 0.05

COLOR_CLARO = [0.85, 0.85, 0.75, 1.0]
COLOR_OSCURO = [0.35, 0.25, 0.15, 1.0]
COLOR_ORIGEN = [1.0, 1.0, 0.0, 1.0]
COLOR_DESTINO = [0.0, 1.0, 0.0, 1.0]


def crear_escena(modo_gui: bool = False) -> tuple[int, dict[str, int]]:
    """Crea una escena de PyBullet con un tablero de ajedrez 8x8.

    Args:
        modo_gui: si es True abre una ventana (p.GUI), si no corre headless
            (p.DIRECT), útil para tests y ejecución sin pantalla.

    Returns:
        Tupla con el client_id de la conexión a PyBullet y un dict que mapea
        notación algebraica (ej. "e4") al body_id de esa casilla.
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
            posicion = [
                (columna - 3.5) * TAMANO_CASILLA,
                (fila - 3.5) * TAMANO_CASILLA,
                ALTO_CASILLA / 2,
            ]
            body_id = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=forma_colision,
                basePosition=posicion,
                physicsClientId=client_id,
            )
            color = COLOR_CLARO if (fila + columna) % 2 == 0 else COLOR_OSCURO
            p.changeVisualShape(body_id, -1, rgbaColor=color, physicsClientId=client_id)
            casillas[casilla] = body_id

    return client_id, casillas


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


def cerrar_escena(client_id: int) -> None:
    """Cierra la conexión a PyBullet asociada al client_id dado."""
    p.disconnect(client_id)
