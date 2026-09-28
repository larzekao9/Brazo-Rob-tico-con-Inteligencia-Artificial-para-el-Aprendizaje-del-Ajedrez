import io
import zipfile
from datetime import datetime, timedelta, timezone

import chess
import chess.pgn
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.modelos.tablas_orm import CalibracionORM, ExportacionDatasetORM, JugadaORM, PartidaORM, UsuarioORM
from backend.servicios.auth.servicio_auth import create_user
from backend.servicios.calibracion import MIN_JUGADAS_PARTIDA_VALIDA
from backend.servicios.entrenamiento.servicio_dataset import (
    SinPartidasValidasError,
    estado_entrenamiento,
    generar_dataset,
    partidas_validas,
)

_RUY_LOPEZ = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]
"""10 plies siempre legales (5 del jugador) — suficiente para pasar
`MIN_JUGADAS_PARTIDA_VALIDA` sin depender de Stockfish."""


@pytest.fixture()
def sesion() -> Session:
    engine = create_engine("sqlite:///:memory:")
    crear_tablas(engine)
    fabrica = crear_fabrica_sesiones(engine)
    with fabrica() as db:
        yield db


def _crear_jugador(db: Session, email: str = "ana@test.com") -> UsuarioORM:
    return create_user(db, email, "Ana", "secreto1", rol="jugador")


def _crear_facilitador(db: Session, email: str = "profe@test.com") -> UsuarioORM:
    return create_user(db, email, "Profe", "secreto1", rol="facilitador")


def _insertar_partida_valida(
    db: Session,
    usuario: UsuarioORM,
    partida_id: str,
    *,
    estado: str = "terminada",
    resultado: str | None = "1-0",
    hace_horas: float = 0,
) -> PartidaORM:
    """Inserta una partida con una secuencia real (Ruy López) y sus jugadas —
    suficientes para pasar `MIN_JUGADAS_PARTIDA_VALIDA` jugadas del jugador."""
    tablero = chess.Board()
    fecha = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hace_horas)
    fila = PartidaORM(
        id=partida_id,
        usuario_id=usuario.id,
        fecha=fecha,
        resultado=resultado,
        tipo="digital",
        fen=chess.STARTING_FEN,
        fen_inicial=chess.STARTING_FEN,
        nivel=10,
        tipo_oponente="motor",
        jugadas_uci="",
        estado=estado,
        actualizada_en=fecha,
    )
    db.add(fila)

    jugadas_uci = []
    for numero, jugada_san in enumerate(_RUY_LOPEZ, start=1):
        fen_antes = tablero.fen()
        movimiento = tablero.parse_san(jugada_san)
        db.add(
            JugadaORM(
                partida_id=partida_id,
                numero=numero,
                fen_antes=fen_antes,
                movimiento=movimiento.uci(),
                decidido_por="jugador" if numero % 2 == 1 else "motor",
                evaluacion_cp=10 * numero,
            )
        )
        jugadas_uci.append(movimiento.uci())
        tablero.push(movimiento)

    fila.fen = tablero.fen()
    fila.jugadas_uci = " ".join(jugadas_uci)
    db.commit()
    return fila


def test_partidas_validas_excluye_en_curso_y_abandonadas(sesion) -> None:
    jugador = _crear_jugador(sesion)
    _insertar_partida_valida(sesion, jugador, "terminada-1", estado="terminada")
    _insertar_partida_valida(sesion, jugador, "en-curso-1", estado="en_curso", resultado=None)
    _insertar_partida_valida(sesion, jugador, "abandonada-1", estado="abandonada", resultado=None)

    validas = partidas_validas(sesion)

    assert [fila.id for fila in validas] == ["terminada-1"]


def test_partidas_validas_excluye_partidas_de_facilitador(sesion) -> None:
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, facilitador, "demo-facilitador")

    assert partidas_validas(sesion) == []


def test_partidas_validas_excluye_pocas_jugadas_del_jugador(sesion) -> None:
    jugador = _crear_jugador(sesion)
    fila = PartidaORM(
        id="corta-1",
        usuario_id=jugador.id,
        fecha=datetime.now(timezone.utc).replace(tzinfo=None),
        resultado="1-0",
        tipo="digital",
        fen=chess.STARTING_FEN,
        fen_inicial=chess.STARTING_FEN,
        nivel=10,
        tipo_oponente="motor",
        jugadas_uci="e2e4 e7e5",  # 1 sola jugada del jugador
        estado="terminada",
    )
    sesion.add(fila)
    sesion.commit()

    assert partidas_validas(sesion) == []


def test_estado_entrenamiento_sin_partidas(sesion) -> None:
    resultado = estado_entrenamiento(sesion)

    assert resultado["partidas_validas_total"] == 0
    assert resultado["partidas_nuevas"] == 0
    assert resultado["progreso"] == 0.0
    assert resultado["listo_para_entrenar"] is False
    assert resultado["ultima_descarga"] is None


def test_estado_entrenamiento_umbral_por_defecto_es_diez(sesion, monkeypatch) -> None:
    monkeypatch.delenv("UMBRAL_PARTIDAS_ENTRENAMIENTO", raising=False)
    assert estado_entrenamiento(sesion)["umbral_partidas"] == 10


def test_estado_entrenamiento_respeta_variable_de_entorno(sesion, monkeypatch) -> None:
    monkeypatch.setenv("UMBRAL_PARTIDAS_ENTRENAMIENTO", "3")
    jugador = _crear_jugador(sesion)
    for i in range(3):
        _insertar_partida_valida(sesion, jugador, f"partida-{i}")

    resultado = estado_entrenamiento(sesion)

    assert resultado["umbral_partidas"] == 3
    assert resultado["partidas_nuevas"] == 3
    assert resultado["progreso"] == 1.0
    assert resultado["listo_para_entrenar"] is True


def test_generar_dataset_sin_partidas_lanza_error_dedicado(sesion) -> None:
    with pytest.raises(SinPartidasValidasError):
        generar_dataset(sesion, facilitador_id=1, solo_nuevas=False)


def test_generar_dataset_arma_zip_con_los_cinco_archivos(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-1")

    contenido, nombre_archivo = generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    assert nombre_archivo.startswith("dataset_ajedrez_") and nombre_archivo.endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(contenido)) as zip_archivo:
        nombres = set(zip_archivo.namelist())
        assert nombres == {"partidas.pgn", "jugadas.csv", "partidas.csv", "manifiesto.json", "LEEME.txt"}


def test_generar_dataset_pgn_se_puede_releer_con_python_chess(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-1")

    contenido, _ = generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    with zipfile.ZipFile(io.BytesIO(contenido)) as zip_archivo:
        texto_pgn = zip_archivo.read("partidas.pgn").decode("utf-8")

    juego = chess.pgn.read_game(io.StringIO(texto_pgn))
    assert juego is not None
    assert juego.headers["Result"] == "1-0"
    jugadas_san = [nodo.san() for nodo in juego.mainline()]
    assert jugadas_san == _RUY_LOPEZ


def test_generar_dataset_csv_tiene_encabezados_esperados(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-1")

    contenido, _ = generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    with zipfile.ZipFile(io.BytesIO(contenido)) as zip_archivo:
        jugadas_csv = zip_archivo.read("jugadas.csv").decode("utf-8-sig")
        partidas_csv = zip_archivo.read("partidas.csv").decode("utf-8-sig")

    assert jugadas_csv.splitlines()[0].split(",")[:3] == ["partida", "numero", "quien"]
    assert partidas_csv.splitlines()[0].split(",")[:2] == ["partida", "jugador"]
    assert "partida-1" in jugadas_csv
    assert "partida-1" in partidas_csv


def test_generar_dataset_es_anonimo_sin_correo_ni_nombre_real(sesion) -> None:
    jugador = _crear_jugador(sesion, email="secreta@test.com")
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-1")

    contenido, _ = generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    with zipfile.ZipFile(io.BytesIO(contenido)) as zip_archivo:
        textos = [
            zip_archivo.read(nombre).decode("utf-8-sig")
            for nombre in ("partidas.pgn", "jugadas.csv", "partidas.csv", "manifiesto.json")
        ]

    for texto in textos:
        assert "secreta@test.com" not in texto
        assert jugador.nombre not in texto
    assert "j_" in textos[0]  # el alias sí aparece, en vez del nombre real


def test_generar_dataset_registra_la_descarga(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-1")

    generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    filas = sesion.query(ExportacionDatasetORM).all()
    assert len(filas) == 1
    assert filas[0].usuario_id == facilitador.id
    assert filas[0].cantidad_partidas == 1
    assert filas[0].cantidad_jugadas == MIN_JUGADAS_PARTIDA_VALIDA
    assert filas[0].formato == "pgn+csv"


def test_partidas_nuevas_tras_una_descarga_ya_no_cuentan(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-vieja")

    generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)
    estado_tras_primera_descarga = estado_entrenamiento(sesion)
    assert estado_tras_primera_descarga["partidas_nuevas"] == 0
    assert estado_tras_primera_descarga["ultima_descarga"]["cantidad_partidas"] == 1

    _insertar_partida_valida(sesion, jugador, "partida-nueva", hace_horas=-1)
    estado_tras_partida_nueva = estado_entrenamiento(sesion)

    assert estado_tras_partida_nueva["partidas_validas_total"] == 2
    assert estado_tras_partida_nueva["partidas_nuevas"] == 1


def test_generar_dataset_solo_nuevas_excluye_las_ya_descargadas(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-vieja")
    generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    with pytest.raises(SinPartidasValidasError):
        generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=True)


def test_generar_dataset_incluye_nivel_y_precision_cuando_hay_calibracion(sesion) -> None:
    jugador = _crear_jugador(sesion)
    facilitador = _crear_facilitador(sesion)
    _insertar_partida_valida(sesion, jugador, "partida-1")
    sesion.add(
        CalibracionORM(
            usuario_id=jugador.id,
            partida_id="partida-1",
            precision_global=87.5,
            nivel_partida=12,
            rango_partida="Intermedio",
            total_jugadas=MIN_JUGADAS_PARTIDA_VALIDA,
        )
    )
    sesion.commit()

    contenido, _ = generar_dataset(sesion, facilitador_id=facilitador.id, solo_nuevas=False)

    with zipfile.ZipFile(io.BytesIO(contenido)) as zip_archivo:
        texto_pgn = zip_archivo.read("partidas.pgn").decode("utf-8")
        partidas_csv = zip_archivo.read("partidas.csv").decode("utf-8-sig")

    assert '[NivelJugador "12"]' in texto_pgn
    assert '[PrecisionJugador "87.50"]' in texto_pgn
    assert "87.50" in partidas_csv
