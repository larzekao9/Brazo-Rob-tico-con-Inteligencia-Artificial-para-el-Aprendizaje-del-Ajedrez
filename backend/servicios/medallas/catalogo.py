"""Catálogo de medallas ("figuritas") que un jugador puede ganar.

**Para agregar una medalla:** sumar una entrada a `CATALOGO` con su código (único y estable: es la clave de la medalla
ganada y de su imagen), su nombre, descripción, nivel, la pieza de su figurita, la `meta` y una función `medir` que, con
los datos del jugador (ver `servicio_medallas.calcular_datos`), devuelve su progreso. Se gana cuando `progreso >= meta`.
No hace falta tocar la base de datos ni la pantalla: el álbum se arma con lo que devuelve el backend, y a quien ya merecía
la medalla se la otorga la próxima vez que se evalúe.

Datos disponibles en `datos`: `terminadas`, `victorias`, `calibradas`, `max_en_un_dia`, `max_dias_semana`, `racha`,
`mejor_precision`, `corono`, `mate_rapido`, `vencio_turing`, `vencio_stockfish_8`, `mensajes_tutor`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

NIVELES = ("bronce", "plata", "oro", "legendaria")
"""De menor a mayor rareza; el orden sirve para elegir las medallas destacadas de un jugador."""

PIEZAS = ("peon", "caballo", "alfil", "torre", "dama", "rey")

MEDALLA_GANADA = 1
"""Convención de las medallas de tipo "sí o no": `medir` devuelve 1 si la cumplió y 0 si no, con `meta=1`."""


@dataclass(frozen=True)
class Medalla:
    """Una medalla del catálogo."""

    codigo: str
    nombre: str
    descripcion: str
    nivel: str
    pieza: str
    meta: int
    medir: Callable[[dict], int]

    def __post_init__(self) -> None:
        if self.nivel not in NIVELES or self.pieza not in PIEZAS or self.meta < 1:
            raise ValueError(f"Medalla mal definida: {self.codigo}")


def _si(condicion: bool) -> int:
    return MEDALLA_GANADA if condicion else 0


CATALOGO: tuple[Medalla, ...] = (
    Medalla("primer_peon", "Primer Peón", "Terminá tu primera partida.", "bronce", "peon", 1, lambda d: d["terminadas"]),
    Medalla("peon_valiente", "Peón Valiente", "Jugá 10 partidas.", "bronce", "peon", 10, lambda d: d["terminadas"]),
    Medalla("salto_de_caballo", "Salto de Caballo", "Ganá tu primera partida.", "bronce", "caballo", 1, lambda d: d["victorias"]),
    Medalla(
        "mente_revelada", "Mente Revelada", "Completá las 3 partidas de diagnóstico y descubrí tu nivel.", "bronce", "dama", 3,
        lambda d: d["calibradas"],
    ),
    Medalla(
        "torre_incansable", "Torre Incansable", "Jugá 5 partidas en un mismo día.", "plata", "torre", 5, lambda d: d["max_en_un_dia"]
    ),
    Medalla(
        "ojo_de_alfil", "Ojo de Alfil", "Jugá una partida con 80 % o más de precisión.", "plata", "alfil", 80,
        lambda d: int(d["mejor_precision"]),
    ),
    Medalla("peon_coronado", "Peón Coronado", "Coroná un peón.", "plata", "peon", 1, lambda d: _si(d["corono"])),
    Medalla(
        "constancia_de_roque", "Constancia de Roque", "Jugá en 3 días distintos de una misma semana.", "plata", "torre", 3,
        lambda d: d["max_dias_semana"],
    ),
    Medalla(
        "mate_relampago", "Mate Relámpago", "Ganá por jaque mate en 20 jugadas o menos.", "oro", "dama", 1,
        lambda d: _si(d["mate_rapido"]),
    ),
    Medalla("rey_de_la_racha", "Rey de la Racha", "Ganá 3 partidas seguidas.", "oro", "rey", 3, lambda d: d["racha"]),
    Medalla("domador_de_turing", "Domador de Turing", "Ganale una partida a Turing.", "oro", "caballo", 1, lambda d: _si(d["vencio_turing"])),
    Medalla(
        "rompe_motores", "Rompe Motores", "Ganale a Stockfish de nivel 8 o más.", "legendaria", "rey", 1,
        lambda d: _si(d["vencio_stockfish_8"]),
    ),
    Medalla(
        "aprendiz_de_turing", "Aprendiz de Turing", "Hacele 10 preguntas al tutor.", "bronce", "alfil", 10,
        lambda d: d["mensajes_tutor"],
    ),
)

POR_CODIGO: dict[str, Medalla] = {m.codigo: m for m in CATALOGO}
if len(POR_CODIGO) != len(CATALOGO):
    raise RuntimeError("Hay códigos de medalla repetidos en el catálogo")


# --- reglas que un facilitador puede elegir al crear una medalla propia ------------------------------------------------
REGLA_MANUAL = "manual"
"""Medalla que no se gana sola: la entrega el facilitador a mano (a un jugador o a todo un curso)."""

REGLAS: dict[str, dict] = {
    "terminadas": {"nombre": "Partidas jugadas", "tipo": "contador", "minimo": 1, "maximo": 500, "unidad": "partidas"},
    "victorias": {"nombre": "Partidas ganadas", "tipo": "contador", "minimo": 1, "maximo": 500, "unidad": "victorias"},
    "racha": {"nombre": "Victorias seguidas", "tipo": "contador", "minimo": 2, "maximo": 50, "unidad": "victorias seguidas"},
    "max_en_un_dia": {"nombre": "Partidas en un mismo día", "tipo": "contador", "minimo": 2, "maximo": 50, "unidad": "partidas en un día"},
    "max_dias_semana": {"nombre": "Días distintos jugados en una semana", "tipo": "contador", "minimo": 2, "maximo": 7, "unidad": "días"},
    "mejor_precision": {"nombre": "Precisión en una partida (%)", "tipo": "contador", "minimo": 50, "maximo": 100, "unidad": "% de precisión"},
    "calibradas": {"nombre": "Partidas de diagnóstico completadas", "tipo": "contador", "minimo": 1, "maximo": 50, "unidad": "diagnósticos"},
    "mensajes_tutor": {"nombre": "Preguntas al tutor", "tipo": "contador", "minimo": 1, "maximo": 500, "unidad": "preguntas"},
    "corono": {"nombre": "Coronar un peón", "tipo": "si_no"},
    "mate_rapido": {"nombre": "Ganar por jaque mate en 20 jugadas o menos", "tipo": "si_no"},
    "vencio_turing": {"nombre": "Ganarle a Turing", "tipo": "si_no"},
    "vencio_stockfish_8": {"nombre": "Ganarle a Stockfish de nivel 8 o más", "tipo": "si_no"},
}
"""Cada regla usa un dato que ya calcula `servicio_medallas.calcular_datos`. Para sumar una regla nueva: calcular el dato allá y
agregar una entrada acá (`contador` con mínimo y máximo, o `si_no`); la pantalla de creación la muestra sola."""

PLANTILLAS: tuple[dict, ...] = (
    {"nombre": "Constante del Club", "descripcion": "Jugá 25 partidas.", "nivel": "plata", "pieza": "peon", "regla": "terminadas", "meta": 25},
    {"nombre": "Racha de Fuego", "descripcion": "Ganá 4 partidas seguidas.", "nivel": "oro", "pieza": "rey", "regla": "racha", "meta": 4},
    {"nombre": "Jugador Madrugador", "descripcion": "Jugá 4 días distintos en una semana.", "nivel": "plata", "pieza": "torre", "regla": "max_dias_semana", "meta": 4},
    {"nombre": "Mente Afilada", "descripcion": "Llegá al 90 % de precisión en una partida.", "nivel": "oro", "pieza": "alfil", "regla": "mejor_precision", "meta": 90},
    {"nombre": "Curioso del Tablero", "descripcion": "Hacele 25 preguntas al tutor.", "nivel": "bronce", "pieza": "alfil", "regla": "mensajes_tutor", "meta": 25},
    {"nombre": "Cazador de Robots", "descripcion": "Ganale una partida a Turing.", "nivel": "oro", "pieza": "caballo", "regla": "vencio_turing", "meta": 1},
    {"nombre": "Campeón del Torneo", "descripcion": "Ganaste el torneo de la clase.", "nivel": "legendaria", "pieza": "rey", "regla": "manual", "meta": 1},
    {"nombre": "Mejor Compañero", "descripcion": "Ayudaste a tus compañeros a mejorar.", "nivel": "oro", "pieza": "dama", "regla": "manual", "meta": 1},
    {"nombre": "Esfuerzo Destacado", "descripcion": "Tu esfuerzo esta semana fue ejemplar.", "nivel": "plata", "pieza": "caballo", "regla": "manual", "meta": 1},
)
"""Ideas de medalla para que el facilitador las use como punto de partida (llenan el formulario con un clic)."""


def medidor_de_regla(regla: str) -> Callable[[dict], int]:
    """La función `medir` de una medalla propia según su regla (las manuales nunca se ganan solas)."""
    if regla == REGLA_MANUAL:
        return lambda datos: 0
    if REGLAS[regla]["tipo"] == "si_no":
        return lambda datos: _si(bool(datos[regla]))
    return lambda datos: int(datos[regla])
