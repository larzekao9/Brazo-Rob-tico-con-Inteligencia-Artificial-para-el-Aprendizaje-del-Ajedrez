import chess

from backend.modelos.partida import Partida


def test_partida_nueva_tiene_valores_por_defecto() -> None:
    partida = Partida()
    assert partida.tipo == "digital"
    assert partida.tipo_oponente == "motor"
    assert partida.nivel == 20
    assert not partida.terminada
    assert partida.resultado is None
    assert partida.jugadas_san == []
    assert partida.creada_en  # se completó algo, no quedó vacío


def test_jugadas_san_reconstruye_las_jugadas_en_orden() -> None:
    partida = Partida()
    partida.tablero.push_san("e4")
    partida.tablero.push_san("e5")
    partida.tablero.push_san("Nf3")
    assert partida.jugadas_san == ["e4", "e5", "Nf3"]


def test_dos_partidas_tienen_ids_distintos() -> None:
    assert Partida().id != Partida().id


def test_jugadas_san_reproduce_desde_un_fen_inicial_no_estandar() -> None:
    # Simula una partida creada a partir de un tablero físico escaneado a
    # mitad de partida (posición tras 1. e4 e5).
    fen_escaneado = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    partida = Partida(tablero=chess.Board(fen_escaneado), fen_inicial=fen_escaneado)
    partida.tablero.push_san("Nf3")
    assert partida.jugadas_san == ["Nf3"]
