import threading
import time

import chess
import chess.engine
import pytest

from backend.servicios.motor import analizar_posicion, analizar_posiciones, calcular_jugada, obtener_variaciones

POSICION_INICIAL = chess.STARTING_FEN
# Mate en 1 para las blancas: Damas en h5, torre puede dar mate.
MATE_EN_UNO = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 3"


@pytest.mark.parametrize(
    "fen",
    [
        POSICION_INICIAL,
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # 1.e4 e5
        "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # 1.e4 c5 (Siciliana)
    ],
)
def test_calcular_jugada_devuelve_jugada_legal(fen: str) -> None:
    tablero = chess.Board(fen)
    jugada_san = calcular_jugada(fen, nivel=5, tiempo_limite=0.2)
    assert tablero.parse_san(jugada_san) in tablero.legal_moves


def test_calcular_jugada_encuentra_mate_en_uno() -> None:
    jugada_san = calcular_jugada(MATE_EN_UNO, nivel=20, tiempo_limite=0.5)
    assert jugada_san == "Qxf7#"


def test_calcular_jugada_valida_nivel() -> None:
    with pytest.raises(ValueError):
        calcular_jugada(POSICION_INICIAL, nivel=21)


def test_calcular_jugada_rechaza_posicion_imposible_sin_llegar_a_stockfish() -> None:
    # 9 damas blancas — sintácticamente es un FEN válido, pero imposible en una
    # partida real. Sin la validación, esto hace que Stockfish se caiga en vez
    # de devolver un error claro (visto en vivo con un FEN mal reconocido).
    fen_imposible = "QQQQQQQQ/QPPPPPPP/8/8/8/8/8/K6k w - - 0 1"
    with pytest.raises(ValueError):
        calcular_jugada(fen_imposible, nivel=5)


def test_analizar_posicion_detecta_mate_forzado() -> None:
    resultado = analizar_posicion(MATE_EN_UNO, nivel=20, tiempo_limite=0.5)
    assert resultado["mate_en"] == 1
    assert resultado["jugada"] == "Qxf7#"


def test_analizar_posicion_incluye_profundidad_nodos_y_variacion() -> None:
    resultado = analizar_posicion(POSICION_INICIAL, nivel=10, tiempo_limite=0.3)
    assert resultado["profundidad"] is not None
    assert resultado["nodos"] is not None
    assert len(resultado["variacion_principal"]) >= 1
    assert resultado["variacion_principal"][0] == resultado["jugada"]


def test_obtener_variaciones_devuelve_multiples_jugadas_con_evaluacion() -> None:
    variaciones = obtener_variaciones(POSICION_INICIAL, nivel=10, num_variaciones=3, tiempo_limite=0.2)
    assert len(variaciones) == 3
    tablero = chess.Board(POSICION_INICIAL)
    for variante in variaciones:
        assert tablero.parse_san(variante["jugada"]) in tablero.legal_moves
        assert "evaluacion_cp" in variante
        assert "mate_en" in variante


def test_analizar_posicion_incluye_variantes_candidatas() -> None:
    resultado = analizar_posicion(POSICION_INICIAL, nivel=10, tiempo_limite=0.3, num_variaciones=3)
    assert len(resultado["variantes_candidatas"]) == 3
    # la primera variante candidata es la misma jugada que "jugada" (la mejor)
    assert resultado["variantes_candidatas"][0]["jugada"] == resultado["jugada"]


# --- analizar_posiciones -----------------------------------------------------

# Posiciones con mate en 1 forzado y una jugada ganadora distinta cada una: el
# resultado de Stockfish es el mismo en cualquier corrida, así que sirven para
# comprobar igualdad y orden contra el bucle secuencial (con una búsqueda por
# tiempo, la profundidad y los nodos varían de una corrida a otra).
POSICIONES_CON_MATE_EN_UNO = [
    (MATE_EN_UNO, "Qxf7#"),
    ("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "Ra8#"),
    ("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2", "Qh4#"),
    ("6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1", "Nf7#"),
    ("k7/8/1K6/8/8/8/8/7R w - - 0 1", "Rh8#"),
]


def test_analizar_posiciones_coincide_con_el_bucle_secuencial_y_conserva_el_orden() -> None:
    posiciones = [POSICION_INICIAL] + [fen for fen, _ in POSICIONES_CON_MATE_EN_UNO]
    esperadas = [jugada for _, jugada in POSICIONES_CON_MATE_EN_UNO]

    secuencial = [analizar_posicion(fen, nivel=20, tiempo_limite=0.3) for fen in posiciones]
    en_paralelo = analizar_posiciones(posiciones, nivel=20, tiempo_limite=0.3, max_motores=3)

    assert len(en_paralelo) == len(posiciones)
    for fen, base, paralelo in zip(posiciones, secuencial, en_paralelo):
        assert set(paralelo) == set(base)
        assert paralelo["mate_en"] == base["mate_en"]
        assert paralelo["evaluacion_cp"] == base["evaluacion_cp"] or fen == POSICION_INICIAL
        assert paralelo["variacion_principal"][0] == paralelo["jugada"]
        assert paralelo["variantes_candidatas"][0]["jugada"] == paralelo["jugada"]
        assert chess.Board(fen).parse_san(paralelo["jugada"]) in chess.Board(fen).legal_moves
    assert [r["jugada"] for r in en_paralelo[1:]] == esperadas
    assert [r["jugada"] for r in secuencial[1:]] == esperadas
    assert [r["mate_en"] for r in en_paralelo[1:]] == [1] * len(POSICIONES_CON_MATE_EN_UNO)


def test_analizar_posiciones_con_una_sola_posicion() -> None:
    resultado = analizar_posiciones([MATE_EN_UNO], nivel=20, tiempo_limite=0.3)

    assert [r["jugada"] for r in resultado] == ["Qxf7#"]


def test_analizar_posiciones_lista_vacia_devuelve_lista_vacia() -> None:
    assert analizar_posiciones([], nivel=20, tiempo_limite=0.3) == []


def test_analizar_posiciones_valida_nivel_fen_y_max_motores_sin_abrir_stockfish(monkeypatch) -> None:
    motores = _instalar_motor_falso(monkeypatch)

    with pytest.raises(ValueError):
        analizar_posiciones([POSICION_INICIAL], nivel=21)
    with pytest.raises(ValueError):
        analizar_posiciones([POSICION_INICIAL, "esto no es un fen"], nivel=5)
    with pytest.raises(ValueError):
        analizar_posiciones([POSICION_INICIAL, "QQQQQQQQ/QPPPPPPP/8/8/8/8/8/K6k w - - 0 1"], nivel=5)
    with pytest.raises(ValueError):
        analizar_posiciones([POSICION_INICIAL], nivel=5, max_motores=0)

    assert motores.abiertos == []


class _MotoresFalsos:
    """Registro de los motores falsos abiertos durante un test."""

    def __init__(self) -> None:
        self.abiertos: list[_MotorFalso] = []
        self.candado = threading.Lock()
        self.fallar_en: str | None = None


class _MotorFalso:
    """Reemplaza a `SimpleEngine`: resultados deterministas según el FEN, con
    demoras distintas por posición para que los hilos terminen desordenados."""

    def __init__(self, registro: _MotoresFalsos) -> None:
        self.registro = registro
        self.cerrado = False
        self.opciones: dict | None = None
        self.analizadas: list[str] = []
        with registro.candado:
            registro.abiertos.append(self)

    def __enter__(self) -> "_MotorFalso":
        return self

    def __exit__(self, *args) -> None:
        self.cerrado = True

    def configure(self, opciones: dict) -> None:
        self.opciones = opciones

    def analyse(self, tablero: chess.Board, limite, multipv: int = 1) -> list[dict]:
        fen = tablero.fen()
        self.analizadas.append(fen)
        time.sleep((sum(map(ord, fen)) % 7) * 0.004)
        if fen == self.registro.fallar_en:
            raise RuntimeError("Stockfish se cayó")
        jugadas = sorted(tablero.legal_moves, key=lambda jugada: jugada.uci())
        centipawns = sum(map(ord, fen)) % 300 - 150
        return [
            {
                "score": chess.engine.PovScore(chess.engine.Cp(centipawns + orden), tablero.turn),
                "pv": [jugada],
                "depth": 12,
                "nodes": 1000 + orden,
            }
            for orden, jugada in enumerate(jugadas[:multipv])
        ]


def _instalar_motor_falso(monkeypatch) -> _MotoresFalsos:
    registro = _MotoresFalsos()
    monkeypatch.setattr(
        chess.engine.SimpleEngine, "popen_uci", lambda ruta: _MotorFalso(registro)
    )
    return registro


def _posiciones_de_una_partida(cantidad: int) -> list[str]:
    """`cantidad` FEN consecutivos de una partida determinista (siempre la primera jugada por orden UCI)."""
    tablero = chess.Board()
    posiciones = []
    for _ in range(cantidad):
        tablero.push(min(tablero.legal_moves, key=lambda jugada: jugada.uci()))
        posiciones.append(tablero.fen())
    return posiciones


def test_analizar_posiciones_devuelve_exactamente_lo_mismo_que_el_bucle_secuencial(monkeypatch) -> None:
    _instalar_motor_falso(monkeypatch)
    posiciones = _posiciones_de_una_partida(12)
    assert len(set(posiciones)) == 12

    secuencial = [analizar_posicion(fen, 7, 0.1, 3) for fen in posiciones]
    en_paralelo = analizar_posiciones(posiciones, 7, 0.1, 3, max_motores=4)

    assert en_paralelo == secuencial


def test_analizar_posiciones_abre_cada_motor_una_vez_y_los_configura_y_cierra(monkeypatch) -> None:
    motores = _instalar_motor_falso(monkeypatch)
    posiciones = _posiciones_de_una_partida(12)

    analizar_posiciones(posiciones, nivel=13, tiempo_limite=0.1, max_motores=4)

    assert len(motores.abiertos) == 4
    assert all(motor.opciones == {"Skill Level": 13} for motor in motores.abiertos)
    assert all(motor.cerrado for motor in motores.abiertos)
    analizadas = [fen for motor in motores.abiertos for fen in motor.analizadas]
    assert sorted(analizadas) == sorted(posiciones)


@pytest.mark.parametrize("cantidad, motores_esperados", [(1, 1), (2, 2), (3, 3), (6, 4)])
def test_analizar_posiciones_no_abre_mas_motores_que_posiciones(monkeypatch, cantidad, motores_esperados) -> None:
    motores = _instalar_motor_falso(monkeypatch)

    analizar_posiciones(_posiciones_de_una_partida(cantidad), nivel=5, tiempo_limite=0.1, max_motores=4)

    assert len(motores.abiertos) == motores_esperados


def test_analizar_posiciones_lista_vacia_no_abre_ningun_motor(monkeypatch) -> None:
    motores = _instalar_motor_falso(monkeypatch)

    assert analizar_posiciones([], nivel=5, tiempo_limite=0.1) == []
    assert motores.abiertos == []


def test_analizar_posiciones_respeta_max_motores(monkeypatch) -> None:
    motores = _instalar_motor_falso(monkeypatch)

    analizar_posiciones(_posiciones_de_una_partida(12), nivel=5, tiempo_limite=0.1, max_motores=1)

    assert len(motores.abiertos) == 1
    assert len(motores.abiertos[0].analizadas) == 12


def test_analizar_posiciones_propaga_el_error_del_motor_y_cierra_todos(monkeypatch) -> None:
    motores = _instalar_motor_falso(monkeypatch)
    posiciones = _posiciones_de_una_partida(12)
    motores.fallar_en = posiciones[5]

    with pytest.raises(RuntimeError, match="se cayó"):
        analizar_posiciones(posiciones, nivel=5, tiempo_limite=0.1, max_motores=4)

    assert len(motores.abiertos) == 4
    assert all(motor.cerrado for motor in motores.abiertos)
