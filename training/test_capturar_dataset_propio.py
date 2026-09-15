import pytest

from training.capturar_dataset_propio import fen_piezas_a_ocupacion


def test_posicion_inicial_estandar() -> None:
    ocupacion = fen_piezas_a_ocupacion("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
    assert ocupacion["a1"] == "white-rook"
    assert ocupacion["e1"] == "white-king"
    assert ocupacion["d8"] == "black-queen"
    assert ocupacion["e8"] == "black-king"
    assert ocupacion["a2"] == "white-pawn"
    assert ocupacion["h7"] == "black-pawn"
    assert "e4" not in ocupacion  # casilla vacía en la posición inicial
    assert len(ocupacion) == 32


def test_posicion_ilegal_con_varias_damas_es_valida_para_etiquetar() -> None:
    # A propósito: no hace falta que sea una partida legal, solo decir qué
    # pieza hay en cada casilla que se ocupó.
    ocupacion = fen_piezas_a_ocupacion("QQQQQQQQ/8/8/8/8/8/8/qqqqqqqq")
    assert ocupacion["a8"] == "white-queen"
    assert ocupacion["h8"] == "white-queen"
    assert ocupacion["a1"] == "black-queen"
    assert len(ocupacion) == 16


def test_tablero_vacio() -> None:
    assert fen_piezas_a_ocupacion("8/8/8/8/8/8/8/8") == {}


def test_menos_de_8_filas_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        fen_piezas_a_ocupacion("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP")


def test_fila_que_no_suma_8_columnas_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        fen_piezas_a_ocupacion("rnbqkbn/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")  # falta una pieza en la primera fila


def test_caracter_invalido_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        fen_piezas_a_ocupacion("xnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
