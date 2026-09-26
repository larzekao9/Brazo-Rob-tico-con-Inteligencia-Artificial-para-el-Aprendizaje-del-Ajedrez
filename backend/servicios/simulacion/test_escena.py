import chess
import pytest

pytest.importorskip("pybullet")
from backend.servicios.simulacion.escena import (
    cargar_formas_visuales_piezas,
    cerrar_escena,
    crear_escena,
    resaltar_jugada,
    sincronizar_piezas,
)


def test_crear_escena_devuelve_64_casillas():
    client_id, casillas, piezas = crear_escena(modo_gui=False)
    try:
        assert len(casillas) == 64
        assert "e4" in casillas
    finally:
        cerrar_escena(client_id)


def test_crear_escena_devuelve_32_piezas_en_posicion_inicial():
    client_id, casillas, piezas = crear_escena(modo_gui=False)
    try:
        assert len(piezas) == 32
        assert set(piezas) == {
            "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
            "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
            "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
            "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8",
        }
        assert len(set(piezas.values())) == 32
    finally:
        cerrar_escena(client_id)


def test_resaltar_jugada_no_tira_excepcion():
    client_id, casillas, piezas = crear_escena(modo_gui=False)
    try:
        resaltar_jugada(casillas, "e2", "e4", client_id)
    finally:
        cerrar_escena(client_id)


def test_sincronizar_piezas_tras_una_jugada_mantiene_32_piezas_en_casillas_correctas():
    client_id, casillas, piezas = crear_escena(modo_gui=False)
    try:
        formas_visuales = cargar_formas_visuales_piezas(client_id)
        tablero = chess.Board()
        tablero.push_san("e4")

        piezas = sincronizar_piezas(client_id, piezas, tablero, formas_visuales)

        assert len(piezas) == 32
        assert "e2" not in piezas
        assert "e4" in piezas
        assert len(set(piezas.values())) == 32
    finally:
        cerrar_escena(client_id)


def test_sincronizar_piezas_con_captura_deja_31_piezas():
    client_id, casillas, piezas = crear_escena(modo_gui=False)
    try:
        formas_visuales = cargar_formas_visuales_piezas(client_id)
        tablero = chess.Board()
        for jugada_san in ("e4", "d5", "exd5"):
            tablero.push_san(jugada_san)

        piezas = sincronizar_piezas(client_id, piezas, tablero, formas_visuales)

        assert len(piezas) == 31
        assert "d5" in piezas
        assert "e4" not in piezas
        assert len(set(piezas.values())) == 31
    finally:
        cerrar_escena(client_id)


def test_sincronizar_piezas_dos_veces_seguidas_no_deja_bodies_colgados():
    import pybullet as p

    client_id, casillas, piezas = crear_escena(modo_gui=False)
    try:
        formas_visuales = cargar_formas_visuales_piezas(client_id)
        cantidad_bodies_inicial = p.getNumBodies(physicsClientId=client_id)

        tablero = chess.Board()
        tablero.push_san("Nf3")
        piezas = sincronizar_piezas(client_id, piezas, tablero, formas_visuales)

        tablero.push_san("Nf6")
        piezas = sincronizar_piezas(client_id, piezas, tablero, formas_visuales)

        assert len(piezas) == 32
        assert p.getNumBodies(physicsClientId=client_id) == cantidad_bodies_inicial
    finally:
        cerrar_escena(client_id)
