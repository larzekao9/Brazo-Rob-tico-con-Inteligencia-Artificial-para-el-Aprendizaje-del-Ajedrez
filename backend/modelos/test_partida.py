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
