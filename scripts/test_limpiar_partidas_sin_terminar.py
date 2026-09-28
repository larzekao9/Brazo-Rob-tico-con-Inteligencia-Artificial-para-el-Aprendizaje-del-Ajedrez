"""Prueba del script de limpieza (B7) contra una base SQLite temporal — nunca
contra la base real (eso lo corre el facilitador a mano, con --ejecutar)."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.database import crear_tablas, obtener_engine
from backend.modelos.tablas_orm import JugadaORM, PartidaORM
from scripts.limpiar_partidas_sin_terminar import main


def _engine(tmp_path, monkeypatch):
    ruta_db = tmp_path / "prueba.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{ruta_db}")
    engine = obtener_engine()
    crear_tablas(engine)
    return engine


def _agregar_partida(
    fabrica, partida_id: str, *, resultado, estado, es_demostracion=False, jugadas_uci="", hace_minutos=0
) -> None:
    fecha = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=hace_minutos)
    with fabrica() as sesion:
        sesion.add(
            PartidaORM(
                id=partida_id,
                fecha=fecha,
                actualizada_en=fecha,
                resultado=resultado,
                tipo="digital",
                fen="fen-cualquiera",
                nivel=10,
                tipo_oponente="motor",
                jugadas_uci=jugadas_uci,
                estado=estado,
                es_demostracion=es_demostracion,
            )
        )
        if jugadas_uci:
            sesion.add(JugadaORM(partida_id=partida_id, numero=1, fen_antes="fen-cualquiera", movimiento="e2e4", decidido_por="jugador"))
        sesion.commit()


def test_simulacro_no_borra_nada(tmp_path, monkeypatch, capsys) -> None:
    engine = _engine(tmp_path, monkeypatch)
    fabrica = sessionmaker(bind=engine)
    _agregar_partida(fabrica, "sin-jugadas", resultado=None, estado="en_curso", hace_minutos=120)
    _agregar_partida(fabrica, "terminada", resultado="1-0", estado="terminada", hace_minutos=120)

    main(["--conservar-minutos", "30"])

    with fabrica() as sesion:
        assert sesion.get(PartidaORM, "sin-jugadas") is not None
        assert sesion.get(PartidaORM, "terminada") is not None
    salida = capsys.readouterr().out
    assert "Simulacro" in salida


def test_ejecutar_borra_solo_las_en_curso_viejas_sin_demo_ni_recientes(tmp_path, monkeypatch) -> None:
    engine = _engine(tmp_path, monkeypatch)
    fabrica = sessionmaker(bind=engine)

    _agregar_partida(fabrica, "vieja-sin-jugadas", resultado=None, estado="en_curso", hace_minutos=120)
    _agregar_partida(
        fabrica, "vieja-con-jugadas", resultado=None, estado="en_curso", jugadas_uci="e2e4 e7e5 g1f3", hace_minutos=120
    )
    _agregar_partida(fabrica, "terminada", resultado="1-0", estado="terminada", hace_minutos=120)
    _agregar_partida(fabrica, "demo", resultado=None, estado="en_curso", es_demostracion=True, hace_minutos=120)
    _agregar_partida(fabrica, "reciente", resultado=None, estado="en_curso", hace_minutos=5)
    _agregar_partida(fabrica, "abandonada", resultado=None, estado="abandonada", hace_minutos=120)

    respaldo = tmp_path / "respaldo.json"
    main(["--ejecutar", "--respaldo", str(respaldo), "--conservar-minutos", "30"])

    with fabrica() as sesion:
        restantes = {fila.id for fila in sesion.scalars(select(PartidaORM))}
    assert restantes == {"terminada", "demo", "reciente", "abandonada"}

    contenido_respaldo = json.loads(respaldo.read_text(encoding="utf-8"))
    ids_respaldados = {fila["id"] for fila in contenido_respaldo["partidas"]}
    assert ids_respaldados == {"vieja-sin-jugadas", "vieja-con-jugadas"}
    assert contenido_respaldo["cantidad_jugadas"] == 1  # solo "vieja-con-jugadas" tenía fila en `jugada`


def test_ejecutar_sin_respaldo_falla_con_argparse_error(tmp_path, monkeypatch, capsys) -> None:
    _engine(tmp_path, monkeypatch)
    try:
        main(["--ejecutar"])
        assert False, "se esperaba SystemExit"
    except SystemExit as error:
        assert error.code != 0
