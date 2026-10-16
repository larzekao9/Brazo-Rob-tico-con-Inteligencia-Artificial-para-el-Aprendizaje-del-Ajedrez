"""Sesión guiada de captura: interpretación de las órdenes y resumen del dataset (sin cámara)."""
import chess

from training.sesion_captura import interpretar_orden, resumen_del_dataset


def test_una_jugada_legal_actualiza_la_posicion_y_pide_foto() -> None:
    tablero = chess.Board()

    nuevo, accion = interpretar_orden(tablero, "e4")

    assert accion == "foto" and nuevo.board_fen().startswith("rnbqkbnr/pppppppp/8/8/4P3")
    assert tablero.board_fen() == chess.Board().board_fen()  # no modifica el original


def test_una_jugada_ilegal_no_cambia_nada() -> None:
    tablero = chess.Board()

    nuevo, accion = interpretar_orden(tablero, "e5")

    assert accion.startswith("error") and nuevo is tablero


def test_deshacer_vuelve_a_la_posicion_anterior() -> None:
    tablero = chess.Board()
    tablero.push_san("e4")

    nuevo, accion = interpretar_orden(tablero, "u")

    assert accion == "foto" and nuevo.board_fen() == chess.Board().board_fen()


def test_deshacer_sin_jugadas_da_error() -> None:
    _, accion = interpretar_orden(chess.Board(), "u")

    assert accion.startswith("error")


def test_una_posicion_libre_con_varias_damas_se_acepta() -> None:
    nuevo, accion = interpretar_orden(chess.Board(), "fen 4k3/8/8/3QQ3/8/8/8/4K2Q")

    assert accion == "foto" and nuevo.board_fen() == "4k3/8/8/3QQ3/8/8/8/4K2Q"


def test_una_posicion_libre_invalida_da_error() -> None:
    _, accion = interpretar_orden(chess.Board(), "fen esto-no-es-un-fen")

    assert accion.startswith("error")


def test_ordenes_de_control() -> None:
    tablero = chess.Board()

    assert interpretar_orden(tablero, "q")[1] == "salir"
    assert interpretar_orden(tablero, "foto")[1] == "foto"
    assert interpretar_orden(tablero, "   ")[1] == "nada"


def test_resumen_cuenta_las_muestras_por_clase(tmp_path) -> None:
    (tmp_path / "white-pawn").mkdir()
    (tmp_path / "vacia").mkdir()
    for i in range(3):
        (tmp_path / "white-pawn" / f"{i}.png").write_bytes(b"x")
    (tmp_path / "vacia" / "0.png").write_bytes(b"x")

    assert resumen_del_dataset(tmp_path) == {"vacia": 1, "white-pawn": 3}
    assert resumen_del_dataset(tmp_path / "no_existe") == {}
