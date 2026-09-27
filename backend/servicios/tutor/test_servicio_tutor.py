"""Tests de `servicio_tutor.py`.

`_llamar_api_groq` siempre queda monkeypatcheada acá — ningún test le pega a
la red real de Groq (ver advertencia al inicio de `servicio_tutor.py` sobre la
forma exacta de la Chat Completions API, todavía sin validar contra la API
real por falta de una `GROQ_API_KEY`).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.modelos.tablas_orm import PartidaORM, UsuarioORM
from backend.servicios.partida.servicio_partida import crear_partida, mover, obtener_partida
from backend.servicios.tutor import servicio_tutor
from backend.servicios.tutor.servicio_tutor import (
    MAX_RONDAS_HERRAMIENTAS,
    MENSAJE_TOPE_RONDAS,
    construir_prompt_sistema,
    procesar_mensaje,
    regla_general_ajedrez,
    regla_pieza,
    resumen_ultima_partida,
)

_TITULOS_PRESET = {
    "infantil": "Modo Infantil",
    "estandar": "Modo Estándar",
    "adultos": "Modo Adultos",
}


# ---------------------------------------------------------------------------
# construir_prompt_sistema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rango", ["Principiante", "Intermedio", "Avanzado"])
@pytest.mark.parametrize("preset", ["infantil", "estandar", "adultos"])
def test_construir_prompt_sistema_combina_tono_y_nivel(rango: str, preset: str) -> None:
    prompt = construir_prompt_sistema(rango, preset)
    assert "Turing" in prompt
    assert f"El jugador es {rango}" in prompt
    assert _TITULOS_PRESET[preset] in prompt
    assert "llamá siempre primero a la tool" in prompt


def test_construir_prompt_sistema_incluye_regla_de_alcance_fuera_de_ajedrez() -> None:
    from backend.servicios.tutor.servicio_tutor import MENSAJE_FUERA_DE_TEMA

    prompt = construir_prompt_sistema()
    assert MENSAJE_FUERA_DE_TEMA in prompt
    assert "ÚNICO tema" in prompt


def test_construir_prompt_sistema_sin_argumentos_cae_en_defaults() -> None:
    prompt = construir_prompt_sistema()
    assert "El jugador es Intermedio" in prompt
    assert _TITULOS_PRESET["estandar"] in prompt


def test_construir_prompt_sistema_valores_no_reconocidos_caen_en_defaults() -> None:
    prompt = construir_prompt_sistema("no-existe", "no-existe")
    assert "El jugador es Intermedio" in prompt
    assert _TITULOS_PRESET["estandar"] in prompt


# ---------------------------------------------------------------------------
# regla_pieza / regla_general_ajedrez
# ---------------------------------------------------------------------------


def test_regla_pieza_con_clave_valida() -> None:
    resultado = regla_pieza("caballo")
    assert resultado["encontrada"] is True
    assert resultado["nombre"] == "Caballo"
    assert resultado["apodo"] == "El Infiltrador"
    assert "como_se_mueve" in resultado
    assert "regla_especial" in resultado


def test_regla_pieza_con_clave_invalida() -> None:
    resultado = regla_pieza("reina")
    assert resultado["encontrada"] is False
    assert "mensaje" in resultado


def test_regla_general_ajedrez_con_clave_valida() -> None:
    resultado = regla_general_ajedrez("jaque_mate")
    assert resultado["encontrada"] is True
    assert "jaque mate" in resultado["texto"].lower()


def test_regla_general_ajedrez_con_clave_invalida() -> None:
    resultado = regla_general_ajedrez("apertura_italiana")
    assert resultado["encontrada"] is False
    assert "mensaje" in resultado


@pytest.mark.parametrize("tema", ["valor_de_las_piezas", "centipawns", "tablero_y_notacion"])
def test_regla_general_ajedrez_cubre_temas_matematicos_del_ajedrez(tema: str) -> None:
    """Estos son temas de ajedrez aunque suenen a matemática (puntos, centipawns, conteo de
    casillas) — no deberían caer en el bloque de "fuera de tema", tienen que estar cubiertos
    acá para que el LLM los explique en vez de negarse."""
    resultado = regla_general_ajedrez(tema)
    assert resultado["encontrada"] is True
    assert resultado["texto"]


# ---------------------------------------------------------------------------
# resumen_ultima_partida
# ---------------------------------------------------------------------------


@pytest.fixture
def db_sqlite():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    crear_tablas(engine)
    fabrica = crear_fabrica_sesiones(engine)
    sesion = fabrica()
    try:
        yield sesion
    finally:
        sesion.close()


def _crear_usuario(db, email: str) -> int:
    usuario = UsuarioORM(email=email, nombre="Jugadora de prueba", password_hash="x", rol="jugador", activo=True)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario.id


def test_resumen_ultima_partida_con_partida_jugada(db_sqlite) -> None:
    usuario_id = _crear_usuario(db_sqlite, "tutor-resumen@test.com")

    # La partida vive en el repositorio en memoria de `servicio_partida` (mismo
    # patrón que `test_servicio_partida.py`); acá se refleja además una fila
    # `PartidaORM` equivalente en la SQLite del test, que es de donde
    # `obtener_historial_partidas` (reusada sin tocar) encuentra el id.
    partida = crear_partida(nivel=1, usuario_id=usuario_id)
    mover(partida.id, "e2e4")
    partida = obtener_partida(partida.id)

    db_sqlite.add(
        PartidaORM(
            id=partida.id,
            usuario_id=usuario_id,
            resultado=None,
            tipo="digital",
            fen=partida.fen,
            fen_inicial=partida.fen_inicial,
            nivel=partida.nivel,
            tipo_oponente=partida.tipo_oponente,
            jugadas_uci=" ".join(m.uci() for m in partida.tablero.move_stack),
        )
    )
    db_sqlite.commit()

    resultado = resumen_ultima_partida(db_sqlite, usuario_id)

    assert resultado["hay_partida"] is True
    assert resultado["partida_id"] == partida.id
    assert resultado["total_jugadas"] == len(partida.jugadas_san)
    assert isinstance(resultado["precision_global"], float)
    assert resultado["consejo_tutor"]
    assert isinstance(resultado["jugadas_destacadas"], list)
    for jugada in resultado["jugadas_destacadas"]:
        assert {"numero_ply", "jugada_san", "calidad", "principio_ajedrecistico", "explicacion"} <= jugada.keys()


def test_resumen_ultima_partida_sin_partidas_devuelve_mensaje(db_sqlite) -> None:
    usuario_id = _crear_usuario(db_sqlite, "tutor-sin-partida@test.com")

    resultado = resumen_ultima_partida(db_sqlite, usuario_id)

    assert resultado["hay_partida"] is False
    assert "mensaje" in resultado


# ---------------------------------------------------------------------------
# procesar_mensaje — loop ReAct con `_llamar_api_groq` monkeypatcheada
# ---------------------------------------------------------------------------


class _LlamadaFuncionFalsa:
    """Imita un `tool_call` de `message.tool_calls` del SDK `openai` (forma de
    la Chat Completions API: `.id`, `.function.name`, `.function.arguments`)."""

    def __init__(self, name: str, arguments: str, call_id: str = "call_1") -> None:
        self.id = call_id
        self.function = SimpleNamespace(name=name, arguments=arguments)

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class _MensajeFalso:
    """Imita `response.choices[0].message` del SDK `openai`."""

    def __init__(self, content: str | None = None, tool_calls: list | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none: bool = False) -> dict:
        datos = {
            "role": "assistant",
            "content": self.content,
            "tool_calls": [tc.model_dump() for tc in self.tool_calls] if self.tool_calls else None,
        }
        if exclude_none:
            datos = {k: v for k, v in datos.items() if v is not None}
        return datos


class _RespuestaFalsa:
    """Imita el objeto que devuelve `client.chat.completions.create(...)`."""

    def __init__(self, message: _MensajeFalso) -> None:
        self.choices = [SimpleNamespace(message=message)]


def test_procesar_mensaje_despacha_tool_y_el_segundo_llamado_tiene_el_formato_correcto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    usuario = SimpleNamespace(id=101, rango_estimado="Principiante", preset_ensenanza="infantil")
    llamadas: list[list[dict]] = []

    def _falso_llamar(mensajes: list[dict], tools: list[dict]):
        llamadas.append(list(mensajes))
        if len(llamadas) == 1:
            return _RespuestaFalsa(
                message=_MensajeFalso(
                    tool_calls=[_LlamadaFuncionFalsa("regla_pieza", json.dumps({"tipo_pieza": "caballo"}))]
                )
            )
        return _RespuestaFalsa(message=_MensajeFalso(content="El caballo se mueve en L."))

    monkeypatch.setattr(servicio_tutor, "_llamar_api_groq", _falso_llamar)

    respuesta = procesar_mensaje(db=None, usuario=usuario, mensaje="¿Cómo se mueve el caballo?")

    assert respuesta == "El caballo se mueve en L."
    assert len(llamadas) == 2

    segundo_input = llamadas[1]
    assert segundo_input[0]["role"] == "system"

    mensaje_asistente = next(m for m in segundo_input if m.get("role") == "assistant")
    assert mensaje_asistente["tool_calls"][0]["function"]["name"] == "regla_pieza"

    mensaje_tool = next(m for m in segundo_input if m.get("role") == "tool")
    assert mensaje_tool["tool_call_id"] == "call_1"
    contenido_tool = json.loads(mensaje_tool["content"])
    assert contenido_tool["encontrada"] is True
    assert contenido_tool["tipo_pieza"] == "caballo"

    historial = servicio_tutor.obtener_historial_tutor(101)
    roles_y_contenidos = [(turno["rol"], turno["contenido"]) for turno in historial]
    assert ("user", "¿Cómo se mueve el caballo?") in roles_y_contenidos
    assert ("assistant", "El caballo se mueve en L.") in roles_y_contenidos


def test_procesar_mensaje_corta_en_el_tope_de_rondas_sin_colgarse(monkeypatch: pytest.MonkeyPatch) -> None:
    usuario = SimpleNamespace(id=202, rango_estimado=None, preset_ensenanza=None)
    contador = {"llamadas": 0}

    def _falso_llamar_siempre_tool(mensajes: list[dict], tools: list[dict]):
        contador["llamadas"] += 1
        return _RespuestaFalsa(
            message=_MensajeFalso(
                tool_calls=[
                    _LlamadaFuncionFalsa(
                        "regla_pieza",
                        json.dumps({"tipo_pieza": "torre"}),
                        call_id=f"call_{contador['llamadas']}",
                    )
                ]
            )
        )

    monkeypatch.setattr(servicio_tutor, "_llamar_api_groq", _falso_llamar_siempre_tool)

    respuesta = procesar_mensaje(db=None, usuario=usuario, mensaje="contame sobre teoría de aperturas")

    assert respuesta == MENSAJE_TOPE_RONDAS
    assert contador["llamadas"] == MAX_RONDAS_HERRAMIENTAS

    historial = servicio_tutor.obtener_historial_tutor(202)
    assert historial[-1]["contenido"] == MENSAJE_TOPE_RONDAS
