"""Todos los parámetros físicos y geométricos del simulador, en un solo lugar.

IMPORTANTE: casi todo es una ESTIMACIÓN (marcada como tal). Ningún valor de las piezas ni de la fricción se midió con el hardware
real; sirven para que el comportamiento sea cualitativamente parecido (la apertura chica choca con la cabeza del caballo, la fuerza
baja con poca fricción deja caer la pieza, etc.) y se corrigen midiendo. Unidades: milímetros, gramos, grados, newtons y segundos,
salvo que el nombre diga otra cosa.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segmento:
    """Un tramo del cuerpo de una pieza: cilindro de diámetro `ancho_x`, o caja `ancho_x` por `ancho_y` si se da `ancho_y`."""

    z_inferior: float
    z_superior: float
    ancho_x: float
    ancho_y: float | None = None


@dataclass(frozen=True)
class PerfilPieza:
    """Forma aproximada de una pieza Staunton de ~30 mm de casilla: tramos apilados desde la base."""

    nombre: str
    masa_g: float
    segmentos: tuple[Segmento, ...]

    @property
    def alto_mm(self) -> float:
        return max(s.z_superior for s in self.segmentos)

    @property
    def ancho_base_mm(self) -> float:
        return self.segmentos[0].ancho_x

    @property
    def ancho_maximo_mm(self) -> float:
        return max(max(s.ancho_x, s.ancho_y or 0.0) for s in self.segmentos)


PERFILES_PIEZAS: dict[str, PerfilPieza] = {
    "p": PerfilPieza("peón", 15.0, (Segmento(0, 6, 12.5), Segmento(6, 12, 9.0), Segmento(12, 20, 7.5), Segmento(20, 30, 11.0))),
    "r": PerfilPieza("torre", 25.0, (Segmento(0, 6, 17.0), Segmento(6, 28, 13.0), Segmento(28, 36, 16.0))),
    "n": PerfilPieza("caballo", 25.0, (Segmento(0, 6, 17.0), Segmento(6, 24, 12.5), Segmento(24, 44, 9.0, 17.0))),
    "b": PerfilPieza("alfil", 24.0, (Segmento(0, 6, 17.0), Segmento(6, 34, 11.0), Segmento(34, 46, 13.0))),
    "q": PerfilPieza("dama", 30.0, (Segmento(0, 6, 19.0), Segmento(6, 40, 12.0), Segmento(40, 52, 16.0))),
    "k": PerfilPieza("rey", 32.0, (Segmento(0, 6, 19.0), Segmento(6, 40, 12.0), Segmento(40, 54, 16.0))),
}
"""ESTIMADO. Anchos de base y cuerpo elegidos para que las aperturas medidas con el brazo real (peón 560 = 14,6 mm entre dedos,
caballo 860 = 22,4 mm) pasen con holgura y la del peón choque con la cabeza del caballo. Masas de piezas con peso (entre 15 y 32 g)."""


@dataclass
class ParametrosFisicos:
    """Física de la pinza, las piezas y el tablero (todo ESTIMADO salvo que se diga lo contrario)."""

    paso_s: float = 1.0 / 240.0
    """Paso fijo de la simulación física."""
    friccion_dedos: float = 0.6
    friccion_piezas: float = 0.6
    """PyBullet multiplica las dos fricciones al haber contacto: 0,36 efectivo, razonable para PLA contra plástico/madera. ESTIMADO."""
    friccion_tablero: float = 0.5
    """Fricción de las piezas con el tablero (el efectivo con la pieza es el producto con `friccion_piezas`). ESTIMADO."""
    friccion_dedos_fallo: float = 0.01
    """Valor que toma la fricción de los dedos con el fallo "dedos resbaladizos" (goma gastada o grasa)."""
    fuerza_total_min_n: float = 28.0
    fuerza_total_max_n: float = 80.0
    """Fuerza total de agarre de la PGE-50-26 a 20 % y 100 % de la fuerza configurada (rango de la ficha técnica, de memoria: confirmar)."""
    velocidad_dedos_max_mm_s: float = 40.0
    """Velocidad con la que cambia la apertura al 100 % de la velocidad de la pinza. ESTIMADO."""
    carrera_mm: float = 26.0
    """Recorrido total entre dedos; igual que `pinza_dh.CARRERA_MM` (se comprueba en los tests)."""
    dedo_grosor_mm: float = 11.5
    dedo_ancho_mm: float = 14.0
    dedo_largo_mm: float = 55.0
    """Dedo largo impreso en PLA: 13 mm del taco de fábrica menos 1,5 de adelgazado en el grosor, 14 de ancho, 13 + 40 de largo
    (ver `scripts/generar_dedos_pinza.py`; el largo total queda por encima del rey)."""
    palma_ancho_mm: float = 44.0
    palma_alto_mm: float = 20.0
    """Cuerpo de la pinza sobre los dedos (caja que choca con piezas demasiado altas). ESTIMADO."""
    longitud_punta_mm: float = 150.0
    """Distancia de la brida (el `GetPose()` del brazo) a las puntas de los dedos. ESTIMADO: fija a qué altura queda el tablero
    en el mundo (superficie = `z_tope` menos esto)."""
    grosor_tablero_mm: float = 12.0
    borde_tablero_mm: float = 15.0
    margen_agarre_tablero_mm: float = 0.5
    """Las puntas no pueden quedar más bajo que el tablero; el comando se rechaza si pide bajar más que `z_tope` menos esto."""
    umbral_contacto_n: float = 0.4
    """Fuerza de contacto dedo-pieza a partir de la cual se considera que la pieza está apretada."""
    inclinacion_pieza_caida_grados: float = 35.0
    """Inclinación a partir de la cual una pieza se considera volcada."""
    fuerza_rotura_n: float = 60.0
    """Fuerza de un dedo (o del brazo) contra una pieza a partir de la cual se la da por dañada. ESTIMADO."""
    aplastamiento_mm: float = 1.0
    """Si una pieza queda hundida más que esto en el tablero (la pinza la apretó contra él), se marca como aplastada."""
    latencia_estado_pinza_s: float = 0.15
    """El registro de estado de agarre sigue mostrando el valor viejo este tiempo después de ordenar un movimiento (como el real)."""
    duracion_inicializacion_s: float = 2.0
    """Cuánto tarda la inicialización de la pinza (los dedos se cierran y se abren)."""
    duracion_recalibracion_s: float = 4.0


@dataclass
class ParametrosRobot:
    """Cinemática esquemática y velocidades del brazo (ESTIMADOS a partir de las medidas publicadas del CR5; ver `cinematica.py`)."""

    velocidad_lineal_max_mm_s: float = 1000.0
    """Velocidad del TCP al 100 % de `v` y 100 % de `SpeedFactor`. ESTIMADO."""
    velocidad_articular_max_grados_s: float = 180.0
    aceleracion_max_mm_s2: float = 3000.0
    """Aceleración del TCP al 100 % de `a`. Es mucho menor que la del CR5 real a propósito: con más, la pinza simulada (dedos de 80 g) se
    desarma por inercia. ESTIMADO."""
    duracion_minima_s: float = 0.15
    orientacion_herramienta: tuple[float, float] = (-180.0, 0.0)
    puerto_modbus_pinza: int = 60000
    maestros_modbus_max: int = 5


@dataclass
class ParametrosSimulador:
    """Agrupa todo para pasarlo de una vez."""

    fisicos: ParametrosFisicos = field(default_factory=ParametrosFisicos)
    robot: ParametrosRobot = field(default_factory=ParametrosRobot)
