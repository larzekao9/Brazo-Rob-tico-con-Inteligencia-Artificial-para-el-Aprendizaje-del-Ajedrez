import pytest
from sqlalchemy import create_engine

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.repositorios.repositorio_partida import RepositorioPartidasPostgres
from backend.servicios.partida import servicio_partida
from backend.servicios.partida.servicio_partida import (
    analisis_completo,
    crear_partida,
    jugadas_legales_desde,
    mover,
    mover_desde_foto,
    obtener_partida,
)


def test_crear_partida_arranca_en_posicion_inicial() -> None:
    partida = crear_partida(nivel=5)
    assert partida.fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")
    assert not partida.terminada
    assert partida.tipo_oponente == "motor"


def test_crear_partida_con_tipo_oponente_no_soportado_lanza_valueerror() -> None:
    # Se valida al crear, sin necesidad de Stockfish corriendo (HU10).
    with pytest.raises(ValueError):
        crear_partida(nivel=5, tipo_oponente="participante")


def test_crear_partida_con_fen_inicial_arranca_en_esa_posicion() -> None:
    # Posición tras 1. e4 e5 — simula lo que devolvería /vision/reconocer.
    fen_tablero_escaneado = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    partida = crear_partida(nivel=5, fen_inicial=fen_tablero_escaneado)
    assert partida.fen == fen_tablero_escaneado
    assert partida.jugadas_san == []  # todavía no se jugó nada *desde* que se cargó


def test_crear_partida_con_fen_inicial_invalido_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        crear_partida(nivel=5, fen_inicial="esto no es un fen")


def test_crear_partida_con_fen_inicial_imposible_lanza_valueerror() -> None:
    # 9 damas blancas — sintácticamente válido, pero imposible en una partida
    # real (visto en vivo con un FEN mal reconocido por visión, que hacía
    # caer a Stockfish más adelante en vez de fallar acá con un error claro).
    fen_imposible = "QQQQQQQQ/QPPPPPPP/8/8/8/8/8/K6k w - - 0 1"
    with pytest.raises(ValueError):
        crear_partida(nivel=5, fen_inicial=fen_imposible)


def test_obtener_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        obtener_partida("no-existe")


def test_mover_aplica_jugada_humana_y_responde_con_stockfish() -> None:
    partida = crear_partida(nivel=5)
    resultado = mover(partida.id, "e2e4")
    assert resultado["jugada_motor"] is not None
    assert not resultado["terminada"]
    # el FEN avanzó: ya no es la posición inicial
    assert "w KQkq - 0 1" not in resultado["fen"]


def test_mover_jugada_ilegal_lanza_valueerror() -> None:
    partida = crear_partida(nivel=5)
    with pytest.raises(ValueError):
        mover(partida.id, "e2e5")


def test_mover_en_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        mover("no-existe", "e2e4")


def test_mover_si_la_estrategia_falla_no_deja_la_jugada_humana_aplicada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reproduce el bug donde, si la estrategia activa (ej. el modelo propio,
    # HU4, devolviendo una jugada SAN ilegal) explota calculando su respuesta,
    # la jugada del humano quedaba igual aplicada en `partida.tablero` — el
    # cliente ve un error y no avanza su FEN local, pero el backend ya había
    # cambiado de turno, y la partida quedaba trabada (cualquier jugada de
    # blancas después se rechazaba como ilegal, porque en el servidor ya le
    # tocaba a negras).
    partida = crear_partida(nivel=5)
    fen_antes = partida.fen

    class _EstrategiaRota:
        def decidir_jugada(self, fen: str) -> str:
            raise ValueError("jugada ilegal simulada")

    monkeypatch.setattr(servicio_partida, "crear_estrategia_jugada", lambda *a, **k: _EstrategiaRota())

    with pytest.raises(ValueError):
        mover(partida.id, "e2e4")

    partida_tras_el_error = obtener_partida(partida.id)
    assert partida_tras_el_error.fen == fen_antes
    assert partida_tras_el_error.jugadas_san == []

    # y se puede reintentar sin que la partida haya quedado corrompida
    monkeypatch.undo()
    resultado = mover(partida.id, "e2e4")
    assert resultado["jugadas"][0] == "e4"


def test_mover_guarda_la_jugada_en_el_repositorio(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reproduce el bug donde `mover()` devolvía el FEN correcto en la
    # respuesta HTTP (armado a mano desde el objeto `Partida` en memoria que
    # ya estaba mutado), pero nunca llamaba a `_repositorio.guardar(...)` —
    # con `RepositorioPartidasEnMemoria` no se notaba, porque `obtener()`
    # devuelve el mismo objeto por referencia, pero con un repositorio real
    # (Postgres/SQLite, activo en cuanto se configura `DATABASE_URL`)
    # `obtener()` reconstruye la partida desde la base en cada llamada, así
    # que la siguiente vez que alguien la pedía (recargar la pantalla, la
    # app móvil al reabrir) volvía a ver la posición de antes de la jugada.
    engine = create_engine("sqlite:///:memory:")
    crear_tablas(engine)
    repositorio_real = RepositorioPartidasPostgres(crear_fabrica_sesiones(engine))
    monkeypatch.setattr(servicio_partida, "_repositorio", repositorio_real)

    partida = crear_partida(nivel=5)
    resultado = mover(partida.id, "e2e4")

    partida_releida = obtener_partida(partida.id)
    assert partida_releida.fen == resultado["fen"]
    assert partida_releida.jugadas_san == resultado["jugadas"]


def test_mover_en_partida_ya_terminada_lanza_valueerror() -> None:
    # Fool's mate armado directo en el tablero, sin pasar por Stockfish, para dejar la
    # partida en jaque mate y probar que `mover` no deja seguir jugando después.
    partida = crear_partida(nivel=1)
    for jugada_san in ["f3", "e5", "g4", "Qh4#"]:
        partida.tablero.push_san(jugada_san)
    assert partida.terminada

    with pytest.raises(ValueError):
        mover(partida.id, "a2a3")


def test_jugadas_legales_desde_devuelve_destinos_del_peon() -> None:
    partida = crear_partida(nivel=5)
    assert jugadas_legales_desde(partida.id, "e2") == ["e3", "e4"]


def test_jugadas_legales_desde_casilla_vacia_devuelve_lista_vacia() -> None:
    partida = crear_partida(nivel=5)
    assert jugadas_legales_desde(partida.id, "e4") == []


def test_jugadas_legales_desde_casilla_invalida_lanza_valueerror() -> None:
    partida = crear_partida(nivel=5)
    with pytest.raises(ValueError):
        jugadas_legales_desde(partida.id, "z9")


def test_jugadas_legales_desde_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        jugadas_legales_desde("no-existe", "e2")


def test_mover_desde_foto_detecta_y_aplica_la_jugada(monkeypatch: pytest.MonkeyPatch) -> None:
    partida = crear_partida(nivel=5)
    # Simula que la cámara/reconocimiento ya vieron la posición tras 1. e4 —
    # detectar_jugada no usa el turno de fen_despues, así que el valor exacto no importa acá.
    fen_despues_e4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    monkeypatch.setattr(servicio_partida, "capturar_foto_tablero", lambda: None)
    monkeypatch.setattr(servicio_partida, "reconocer_tablero", lambda imagen, turno: fen_despues_e4)

    resultado = mover_desde_foto(partida.id)

    assert resultado["jugadas"][0] == "e4"
    assert resultado["jugada_motor"] is not None  # requiere Stockfish


def test_mover_desde_foto_sin_jugada_legal_que_coincida_lanza_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partida = crear_partida(nivel=5)
    # Posición imposible de alcanzar con una sola jugada legal desde la inicial.
    fen_irreconciliable = "8/8/8/8/8/8/8/8 b - - 0 1"
    monkeypatch.setattr(servicio_partida, "capturar_foto_tablero", lambda: None)
    monkeypatch.setattr(servicio_partida, "reconocer_tablero", lambda imagen, turno: fen_irreconciliable)

    with pytest.raises(ValueError):
        mover_desde_foto(partida.id)


def test_mover_desde_foto_en_partida_ya_terminada_lanza_valueerror() -> None:
    partida = crear_partida(nivel=1)
    for jugada_san in ["f3", "e5", "g4", "Qh4#"]:
        partida.tablero.push_san(jugada_san)
    assert partida.terminada

    with pytest.raises(ValueError):
        mover_desde_foto(partida.id)


def test_mover_desde_foto_en_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        mover_desde_foto("no-existe")


def test_analisis_completo_devuelve_un_item_por_jugada_con_evaluaciones_invertidas() -> None:
    partida = crear_partida(nivel=1)
    mover(partida.id, "e2e4")

    resultado = analisis_completo(partida.id, tiempo_limite=0.1)

    assert resultado["partida_id"] == partida.id
    assert len(resultado["jugadas"]) == len(partida.jugadas_san)

    primera = resultado["jugadas"][0]
    assert primera["numero_ply"] == 1
    assert primera["color"] == "blanco"
    assert primera["jugada_san"] == "e4"
    assert primera["fen_antes"].startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")
    assert "evaluacion_cp" in primera
    assert "mejor_jugada_motor" in primera
    assert len(primera["variantes_candidatas"]) > 0


def test_analisis_completo_en_partida_inexistente_lanza_keyerror() -> None:
    with pytest.raises(KeyError):
        analisis_completo("no-existe")
