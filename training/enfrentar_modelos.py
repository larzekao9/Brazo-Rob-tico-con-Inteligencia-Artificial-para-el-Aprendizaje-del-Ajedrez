"""Enfrentamientos de partidas completas: modelo contra modelo y modelo contra Stockfish (HU4).

La precisión de predicción (`evaluar_modelo.py`) mide si el modelo imita a un maestro, pero no si JUEGA mejor.
Este módulo mide lo segundo: juega partidas enteras con la misma lógica que usa la aplicación
(`predecir_jugada_maestra`: red neuronal + filtro táctico) y cuenta victorias, tablas y derrotas.

Cada apertura se juega dos veces, cambiando de color, para que ningún lado tenga ventaja. Como el modelo en modo
maestro es determinista, la variedad sale de las aperturas: hay que dar varias.

Stockfish aparece solo como rival de comparación (regla 1 de `CLAUDE.md`): el modelo decide sus jugadas sin consultarlo.

Uso:
    python -m training.enfrentar_modelos --a training/checkpoints/modelo_jugadas_v5_2026-09-24.pt \
        --b training/checkpoints/modelo_jugadas_v6_2026-10-12.pt --niveles-stockfish 8 12 16 20
"""
from __future__ import annotations

import argparse
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine

Jugador = Callable[[str], str]
"""Una función `fen -> jugada en SAN`."""

MAX_JUGADAS_MEDIAS = 240
"""Tope de media-jugadas por partida: si se alcanza, se da por tablas (evita partidas interminables)."""

APERTURAS_UCI: list[str] = [
    "e2e4 e7e5 g1f3 b8c6",
    "e2e4 e7e5 g1f3 g8f6",
    "e2e4 c7c5 g1f3 d7d6",
    "e2e4 c7c5 g1f3 b8c6",
    "e2e4 e7e6 d2d4 d7d5",
    "e2e4 c7c6 d2d4 d7d5",
    "e2e4 d7d5 e4d5 d8d5",
    "e2e4 g8f6 e4e5 f6d5",
    "d2d4 d7d5 c2c4 e7e6",
    "d2d4 d7d5 c2c4 c7c6",
    "d2d4 g8f6 c2c4 e7e6",
    "d2d4 g8f6 c2c4 g7g6",
    "d2d4 f7f5 g2g3 g8f6",
    "c2c4 e7e5 b1c3 g8f6",
    "c2c4 c7c5 g1f3 g8f6",
    "g1f3 d7d5 g2g3 g8f6",
    "g1f3 g8f6 c2c4 e7e6",
    "e2e4 e7e5 f1c4 g8f6",
    "e2e4 e7e5 b1c3 g8f6",
    "d2d4 d7d5 g1f3 g8f6",
]


@dataclass
class Marcador:
    """Resultado de un enfrentamiento desde el punto de vista de `A`."""

    victorias_a: int = 0
    tablas: int = 0
    victorias_b: int = 0

    @property
    def partidas(self) -> int:
        return self.victorias_a + self.tablas + self.victorias_b

    @property
    def puntaje_a(self) -> float:
        """Fracción de puntos de A: victoria = 1, tabla = 0,5, derrota = 0."""
        return (self.victorias_a + 0.5 * self.tablas) / self.partidas if self.partidas else 0.5


def diferencia_elo(puntaje: float) -> float:
    """Diferencia de Elo que corresponde a un puntaje (fórmula logística estándar). Se acota para no dar infinito."""
    acotado = min(max(puntaje, 0.005), 0.995)
    return -400.0 * math.log10(1.0 / acotado - 1.0)


def intervalo_elo(marcador: Marcador) -> tuple[float, float]:
    """Intervalo de confianza aproximado del 95 % para la diferencia de Elo (aproximación normal del puntaje)."""
    n = marcador.partidas
    if n == 0:
        return (0.0, 0.0)
    p = marcador.puntaje_a
    # Varianza por partida de un resultado en {0, 0,5, 1}.
    varianza = (
        marcador.victorias_a * (1 - p) ** 2 + marcador.tablas * (0.5 - p) ** 2 + marcador.victorias_b * p**2
    ) / n
    margen = 1.96 * math.sqrt(varianza / n)
    return diferencia_elo(p - margen), diferencia_elo(p + margen)


def jugar_partida(blancas: Jugador, negras: Jugador, apertura_uci: str = "", max_jugadas: int = MAX_JUGADAS_MEDIAS) -> str:
    """Juega una partida y devuelve `"1-0"`, `"0-1"` o `"1/2-1/2"`.

    Una jugada ilegal de un jugador cuenta como derrota suya (no debería pasar con el modelo ni con Stockfish).
    """
    tablero = chess.Board()
    for uci in apertura_uci.split():
        tablero.push_uci(uci)
    while not tablero.is_game_over(claim_draw=True):
        if len(tablero.move_stack) >= max_jugadas:
            return "1/2-1/2"
        jugador = blancas if tablero.turn == chess.WHITE else negras
        try:
            tablero.push_san(jugador(tablero.fen()))
        except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError):
            return "0-1" if tablero.turn == chess.WHITE else "1-0"
    return tablero.result(claim_draw=True)


def enfrentar(a: Jugador, b: Jugador, aperturas: list[str], al_terminar_partida: Callable[[int, int], None] | None = None) -> Marcador:
    """A contra B en todas las aperturas, una vez con cada color."""
    marcador = Marcador()
    total = 2 * len(aperturas)
    jugadas = 0
    for apertura in aperturas:
        for a_juega_blancas in (True, False):
            resultado = jugar_partida(a, b, apertura) if a_juega_blancas else jugar_partida(b, a, apertura)
            if resultado == "1/2-1/2":
                marcador.tablas += 1
            elif (resultado == "1-0") == a_juega_blancas:
                marcador.victorias_a += 1
            else:
                marcador.victorias_b += 1
            jugadas += 1
            if al_terminar_partida:
                al_terminar_partida(jugadas, total)
    return marcador


def jugador_modelo(ruta_checkpoint: str | Path) -> Jugador:
    """El modelo tal como juega en la aplicación (modo maestro: red + filtro táctico, sin Stockfish)."""
    from backend.servicios.aprendizaje.inferencia import predecir_jugada_maestra

    return lambda fen: predecir_jugada_maestra(fen, ruta_checkpoint=ruta_checkpoint)


class JugadorStockfish:
    """Stockfish a un nivel (`Skill Level` 0-20) con un motor persistente, para no abrir un proceso por jugada."""

    def __init__(self, nivel: int, tiempo_limite: float = 0.05) -> None:
        from backend.servicios.motor.motor_ajedrez import STOCKFISH_PATH

        self._motor = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self._motor.configure({"Skill Level": nivel})
        self._limite = chess.engine.Limit(time=tiempo_limite)

    def __call__(self, fen: str) -> str:
        tablero = chess.Board(fen)
        return tablero.san(self._motor.play(tablero, self._limite).move)

    def cerrar(self) -> None:
        self._motor.quit()


class JugadorStockfishElo(JugadorStockfish):
    """Stockfish con fuerza limitada a un ELO calibrado (`UCI_Elo`, de 1320 a 3190), en vez del `Skill Level` 0-20.

    El ELO de Stockfish está calibrado para partidas con control de tiempo largo; con tiempos de décimas de segundo
    por jugada no es exacto, así que el ELO que se estime de Turing es **relativo a este rival y a este tiempo**.
    """

    ELO_MIN, ELO_MAX = 1320, 3190

    def __init__(self, elo: int, tiempo_limite: float = 0.2) -> None:
        from backend.servicios.motor.motor_ajedrez import STOCKFISH_PATH

        self.elo = max(self.ELO_MIN, min(self.ELO_MAX, elo))
        self._motor = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self._motor.configure({"UCI_LimitStrength": True, "UCI_Elo": self.elo})
        self._limite = chess.engine.Limit(time=tiempo_limite)


def _esperado(elo_propio: float, elo_rival: float) -> float:
    """Puntaje esperado (0 a 1) de un jugador de `elo_propio` contra uno de `elo_rival`."""
    return 1.0 / (1.0 + 10.0 ** ((elo_rival - elo_propio) / 400.0))


def estimar_elo(resultados: list[tuple[float, Marcador]]) -> tuple[float, float, float]:
    """Estima el ELO de A a partir de sus resultados contra rivales de ELO conocido.

    Busca el ELO para el cual el puntaje esperado total coincide con el obtenido (máxima verosimilitud logística). Devuelve
    `(estimación, límite inferior, límite superior)`; el intervalo del 95 % sale de la información de Fisher y es aproximado
    (se achata con pocas partidas, y si A ganó o perdió TODO la estimación solo tiene una cota: se acota a ±800 del rival
    extremo). Los rivales sin partidas se ignoran.
    """
    datos = [(float(elo), marcador) for elo, marcador in resultados if marcador.partidas > 0]
    if not datos:
        raise ValueError("No hay partidas para estimar el ELO")

    def sobrante(elo_a: float) -> float:
        return sum(m.partidas * (m.puntaje_a - _esperado(elo_a, elo)) for elo, m in datos)

    bajo, alto = min(e for e, _ in datos) - 800.0, max(e for e, _ in datos) + 800.0
    for _ in range(80):  # bisección: `sobrante` decrece al subir el ELO
        medio = (bajo + alto) / 2
        if sobrante(medio) > 0:
            bajo = medio
        else:
            alto = medio
    estimacion = (bajo + alto) / 2

    k = math.log(10) / 400.0
    informacion = sum(m.partidas * _esperado(estimacion, e) * (1 - _esperado(estimacion, e)) for e, m in datos) * k * k
    margen = 1.96 / math.sqrt(informacion) if informacion > 1e-12 else 800.0
    return estimacion, estimacion - margen, estimacion + margen


def _linea(etiqueta: str, marcador: Marcador) -> str:
    bajo, alto = intervalo_elo(marcador)
    return (
        f"{etiqueta:<28} +{marcador.victorias_a:>2} ={marcador.tablas:>2} -{marcador.victorias_b:>2}  "
        f"puntaje {marcador.puntaje_a:>6.1%}  Elo {diferencia_elo(marcador.puntaje_a):>+5.0f} [{bajo:>+5.0f}, {alto:>+5.0f}]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", required=True, help="checkpoint del modelo A (la versión anterior)")
    parser.add_argument("--b", required=True, help="checkpoint del modelo B (la versión nueva)")
    parser.add_argument("--aperturas", type=int, default=len(APERTURAS_UCI), help="cuántas aperturas usar (2 partidas c/u)")
    parser.add_argument("--niveles-stockfish", type=int, nargs="*", default=[], help="niveles de Stockfish contra los que medir")
    parser.add_argument("--aperturas-stockfish", type=int, default=10, help="aperturas por nivel contra Stockfish")
    parser.add_argument("--tiempo-stockfish", type=float, default=0.05, help="segundos por jugada de Stockfish")
    args = parser.parse_args()

    modelo_a, modelo_b = jugador_modelo(args.a), jugador_modelo(args.b)

    def avance(hechas: int, total: int) -> None:
        if hechas % 10 == 0 or hechas == total:
            print(f"  ... {hechas}/{total} partidas", flush=True)

    print(f"\n== {Path(args.b).stem} (B) contra {Path(args.a).stem} (A) ==")
    t0 = time.time()
    modelo_contra_modelo = enfrentar(modelo_a, modelo_b, APERTURAS_UCI[: args.aperturas], avance)
    # `enfrentar` cuenta desde A; se muestra desde la nueva versión (B).
    desde_b = Marcador(modelo_contra_modelo.victorias_b, modelo_contra_modelo.tablas, modelo_contra_modelo.victorias_a)
    print(_linea("nueva (B) vs anterior (A)", desde_b), f"({time.time() - t0:.0f}s)")

    for nivel in args.niveles_stockfish:
        print(f"\n== Contra Stockfish nivel {nivel} ({args.tiempo_stockfish}s por jugada) ==")
        for etiqueta, ruta in (("anterior (A)", args.a), ("nueva (B)", args.b)):
            rival = JugadorStockfish(nivel, args.tiempo_stockfish)
            try:
                marcador = enfrentar(jugador_modelo(ruta), rival, APERTURAS_UCI[: args.aperturas_stockfish])
            finally:
                rival.cerrar()
            print(_linea(f"{etiqueta} vs SF{nivel}", marcador), flush=True)


if __name__ == "__main__":
    main()
