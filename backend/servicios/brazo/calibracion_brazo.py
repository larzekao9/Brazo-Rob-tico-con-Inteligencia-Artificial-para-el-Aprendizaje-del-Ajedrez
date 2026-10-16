"""Calibración del brazo contra el tablero real: posición cero y 3 casillas enseñadas a mano (a1, h1 y a8).

Se enseña una sola vez, llevando el brazo a mano (modo arrastre) sobre cada punto y leyendo su pose con `GetPose()`
(`scripts/calibrar_brazo_tablero.py`). De ahí salen la posición cero, la orientación de la herramienta y la posición XYZ de las 64
casillas (`calibracion_tablero.calcular_posiciones_casillas`). Es un archivo local de cada instalación: no se sube a git.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from backend.servicios.brazo.calibracion_tablero import PuntoCalibracion, calcular_posiciones_casillas

ARCHIVO_CALIBRACION_BRAZO = Path(
    os.environ.get("CALIBRACION_BRAZO_ARCHIVO", str(Path(__file__).resolve().parents[3] / "calibracion_local" / "brazo.json"))
)
CASILLAS_ENSENADAS = ("a1", "h1", "a8")
CASILLAS_OPCIONALES = ("h8",)
"""h8 se puede enseñar además: con 4 puntos el ajuste reparte el error de medición en vez de acumularlo en la esquina opuesta."""
RESIDUO_AVISO_MM = 4.0
"""Si algún punto enseñado queda a más de esto de donde lo pone la grilla ajustada, se avisa."""
TOLERANCIA_INCLINACION_GRADOS = 10.0
"""Máxima diferencia de `rx` y `ry` (hacia dónde apunta la pinza) entre los puntos enseñados: tiene que apuntar igual al tablero."""
TOLERANCIA_GIRO_GRADOS = 30.0
"""Máxima diferencia de `rz` (giro de la muñeca sobre su eje). Es más permisivo: girar la pinza no mueve su punta."""
MARGEN_POR_DEBAJO_DE_A1_MM = 5.0
"""Si h1 o a8 se enseñaron más de esto POR DEBAJO de a1 se avisa: la altura del tablero sale de a1, y un punto más bajo sugiere que
a1 se enseñó demasiado arriba (la pinza quedaría en el aire) o que el tablero está inclinado."""
ALTURA_MAXIMA_SOBRE_A1_MM = 60.0
"""h1 y a8 solo aportan X e Y, y se pueden enseñar con la pinza un poco más arriba que en a1; pero muy arriba, un pequeño desvío de
la inclinación corre la posición lateral. Más alto que esto se rechaza."""


@dataclass
class CalibracionBrazo:
    """Lo que necesita `EjecutorReal` para mover piezas."""

    angulos_cero: tuple[float, ...]
    orientacion: tuple[float, float, float]
    posiciones_casillas: dict[str, tuple[float, float, float]]
    avisos: tuple[str, ...] = ()


def _diferencia_angular(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def construir_calibracion(angulos_cero: tuple[float, ...], puntos: dict[str, tuple[float, ...]]) -> CalibracionBrazo:
    """Arma la calibración a partir de la posición cero y las 3 poses `(x, y, z, rx, ry, rz)` enseñadas.

    La orientación es la del punto a1. Se descarta (con error) si otro punto difiere más de `TOLERANCIA_ORIENTACION_GRADOS`.

    La altura de todas las casillas es la de a1 (el tablero es plano): a1 se enseña apoyando la pinza con cuidado sobre el tablero.
    De h1 y a8 solo se usan X e Y, así que se pueden enseñar con la pinza algo más arriba para ver mejor el centro de la casilla.

    Raises:
        ValueError: si faltan casillas, algún dato tiene el largo equivocado, las orientaciones no coinciden o h1 o a8 se
            enseñaron más de `ALTURA_MAXIMA_SOBRE_A1_MM` por encima de a1.
    """
    if not set(CASILLAS_ENSENADAS) <= set(puntos) <= set(CASILLAS_ENSENADAS + CASILLAS_OPCIONALES):
        raise ValueError(f"Hay que enseñar las casillas {CASILLAS_ENSENADAS} (y opcionalmente {CASILLAS_OPCIONALES})")
    if len(angulos_cero) != 6 or any(len(p) != 6 for p in puntos.values()):
        raise ValueError("La posición cero necesita 6 ángulos y cada punto 6 valores (x, y, z, rx, ry, rz)")
    referencia = puntos["a1"][3:]
    for casilla, pose in puntos.items():
        inclinacion = max(_diferencia_angular(a, b) for a, b in zip(pose[3:5], referencia[:2]))
        giro = _diferencia_angular(pose[5], referencia[2])
        if inclinacion > TOLERANCIA_INCLINACION_GRADOS or giro > TOLERANCIA_GIRO_GRADOS:
            raise ValueError(
                f"La orientación de la herramienta en {casilla} {tuple(round(v, 1) for v in pose[3:])} difiere demasiado de la de "
                f"a1 {tuple(round(v, 1) for v in referencia)}: volvé a enseñarlo con la pinza apuntando igual al tablero"
            )
    alturas = {casilla: pose[2] for casilla, pose in puntos.items()}
    altura = alturas["a1"]
    for casilla in ("h1", "a8"):
        if alturas[casilla] - altura > ALTURA_MAXIMA_SOBRE_A1_MM:
            raise ValueError(
                f"{casilla} se enseñó {alturas[casilla] - altura:.0f} mm por encima de a1 (máximo {ALTURA_MAXIMA_SOBRE_A1_MM:.0f} mm): "
                "bajá la pinza para que la posición lateral sea precisa"
            )
    avisos = tuple(
        f"{casilla} quedó {altura - alturas[casilla]:.1f} mm por DEBAJO de a1 (z={alturas[casilla]:.1f} contra {altura:.1f}): la altura del "
        "tablero se toma de a1; si a1 quedó demasiado arriba la pinza no llegaría a las piezas. Comprobalo bajando sobre a1."
        for casilla in ("h1", "a8")
        if altura - alturas[casilla] > MARGEN_POR_DEBAJO_DE_A1_MM
    )
    posiciones = calcular_posiciones_casillas([PuntoCalibracion(c, puntos[c][0], puntos[c][1], altura) for c in puntos])
    for casilla, pose in puntos.items():
        residuo = ((posiciones[casilla][0] - pose[0]) ** 2 + (posiciones[casilla][1] - pose[1]) ** 2) ** 0.5
        if residuo > RESIDUO_AVISO_MM:
            avisos += (f"{casilla} quedó a {residuo:.1f} mm de donde la grilla ajustada la pone: revisá si está bien centrada",)
    return CalibracionBrazo(tuple(float(v) for v in angulos_cero), tuple(float(v) for v in referencia), posiciones, avisos)


def guardar_calibracion_brazo(
    angulos_cero: tuple[float, ...], puntos: dict[str, tuple[float, ...]], ruta: Path | None = None
) -> CalibracionBrazo:
    """Valida y guarda lo enseñado; devuelve la calibración resultante."""
    calibracion = construir_calibracion(angulos_cero, puntos)
    destino = Path(ruta or ARCHIVO_CALIBRACION_BRAZO)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"angulos_cero": list(angulos_cero), "puntos": {c: list(p) for c, p in puntos.items()}}, indent=2),
        encoding="utf-8",
    )
    return calibracion


def cargar_calibracion_brazo(ruta: Path | None = None) -> CalibracionBrazo | None:
    """La calibración guardada, o `None` si todavía no se enseñó.

    Raises:
        ValueError: si el archivo existe pero está dañado o incompleto.
    """
    origen = Path(ruta or ARCHIVO_CALIBRACION_BRAZO)
    if not origen.exists():
        return None
    try:
        datos = json.loads(origen.read_text(encoding="utf-8"))
        return construir_calibracion(tuple(datos["angulos_cero"]), {c: tuple(p) for c, p in datos["puntos"].items()})
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"El archivo de calibración del brazo {origen} está dañado: volvé a enseñarlo") from error


ALIAS_POSICION_CERO = "DESCANSO"
"""Nombre (alias) que se le pone en DobotStudio al punto de la posición cero."""


def puntos_desde_dobotstudio(ruta: Path) -> tuple[tuple[float, ...], dict[str, tuple[float, ...]]]:
    """Lee el archivo `point.json` de un proyecto de DobotStudio Pro (puntos enseñados con el jog) y devuelve `(angulos_cero, puntos)`.

    Cada punto del archivo trae su `alias`, su `pose` `[x, y, z, rx, ry, rz]` y sus ángulos `joint`. Se toman los de alias
    `A1`, `H1`, `A8` (y `H8` si está) para el tablero y el de alias `DESCANSO` para la posición cero (de ese se usan los ángulos
    de las articulaciones, que fijan la postura sin ambigüedad). Los alias no distinguen mayúsculas de minúsculas. Solo se aceptan
    puntos con `tool` y `user` en 0: con otro sistema de coordenadas las poses no serían comparables.

    Raises:
        ValueError: si el archivo no se puede leer, falta algún punto necesario o algún punto usa otra herramienta o usuario.
    """
    try:
        registros = json.loads(Path(ruta).read_text(encoding="utf-8"))
        if not isinstance(registros, list):
            raise TypeError("se esperaba una lista de puntos")
        por_alias = {str(r["alias"]).strip().upper(): r for r in registros}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"No se pudo leer {ruta}: ¿es el point.json de un proyecto de DobotStudio?") from error

    requeridos = [c.upper() for c in CASILLAS_ENSENADAS] + [ALIAS_POSICION_CERO]
    faltan = [alias for alias in requeridos if alias not in por_alias]
    if faltan:
        raise ValueError(f"Faltan puntos en el archivo (alias): {faltan}. Hay: {sorted(por_alias)}")

    puntos: dict[str, tuple[float, ...]] = {}
    for casilla in CASILLAS_ENSENADAS + CASILLAS_OPCIONALES:
        registro = por_alias.get(casilla.upper())
        if registro is None:
            continue
        if registro.get("tool", 0) != 0 or registro.get("user", 0) != 0:
            raise ValueError(f"El punto {casilla} usa tool={registro.get('tool')} y user={registro.get('user')}: tiene que ser 0 y 0")
        puntos[casilla] = tuple(float(v) for v in registro["pose"])
    angulos_cero = tuple(float(v) for v in por_alias[ALIAS_POSICION_CERO]["joint"])
    return angulos_cero, puntos
