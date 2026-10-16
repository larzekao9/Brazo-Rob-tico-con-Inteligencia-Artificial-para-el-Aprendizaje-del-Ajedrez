"""Mide el ELO aproximado de un modelo de Turing jugando contra Stockfish con ELO calibrado (`UCI_Elo`).

Cada rival juega todas las aperturas con los dos colores. Con los resultados se estima el ELO de Turing (máxima verosimilitud)
y su intervalo de confianza aproximado. Es una medición **relativa a este rival, a este tiempo por jugada y a estas
aperturas** (ver `JugadorStockfishElo`), pensada para comparar versiones entre sí y ubicar el orden de magnitud.

Uso:
    python -m training.medir_elo --checkpoint training/checkpoints/modelo_jugadas_v6_2026-10-12.pt \
        --elos 1320 1500 1700 --aperturas 20 --tiempo 0.2

Si Turing pierde (o gana) todas las partidas contra todos los rivales, el ELO queda solo acotado: conviene agregar rivales
más débiles (mínimo 1320) o más fuertes hasta que haya resultados mixtos.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from training.enfrentar_modelos import (
    APERTURAS_UCI,
    JugadorStockfishElo,
    Marcador,
    diferencia_elo,
    enfrentar,
    estimar_elo,
    jugador_turing,
)


def medir(
    ruta_checkpoint: str,
    elos: list[int],
    aperturas: int,
    tiempo: float,
    profundidad: int = 0,
    peso_red: float = 40.0,
    tiempo_busqueda: float | None = 1.0,
    ruta_valor: str | None = None,
) -> list[tuple[int, Marcador]]:
    """Juega contra cada ELO de `elos` y devuelve `[(elo_rival, marcador_de_turing), ...]`.

    Con `profundidad` > 0 Turing usa también la búsqueda de variantes; con 0, solo la red."""
    resultados: list[tuple[int, Marcador]] = []
    for elo in elos:
        rival = JugadorStockfishElo(elo, tiempo)
        try:
            t0 = time.time()
            marcador = enfrentar(jugador_turing(ruta_checkpoint, profundidad, tiempo_busqueda, peso_red, ruta_valor), rival, APERTURAS_UCI[:aperturas])
        finally:
            rival.cerrar()
        resultados.append((rival.elo, marcador))
        print(
            f"  vs Stockfish {rival.elo}: +{marcador.victorias_a} ={marcador.tablas} -{marcador.victorias_b}  "
            f"puntaje {marcador.puntaje_a:.1%}  ({time.time() - t0:.0f}s)",
            flush=True,
        )
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", required=True, help="modelo de Turing a medir (.pt)")
    parser.add_argument("--elos", type=int, nargs="+", default=[1320, 1500, 1700], help="ELO de los rivales de Stockfish")
    parser.add_argument("--aperturas", type=int, default=len(APERTURAS_UCI), help="aperturas por rival (2 partidas c/u)")
    parser.add_argument("--tiempo", type=float, default=0.2, help="segundos por jugada de Stockfish")
    parser.add_argument("--busqueda", type=int, default=0, help="profundidad de búsqueda de Turing (0 = red sola)")
    parser.add_argument("--peso-red", type=float, default=40.0, help="peso de la red frente al cálculo en la búsqueda")
    parser.add_argument("--tiempo-busqueda", type=float, default=1.0, help="segundos máximos por jugada de la búsqueda")
    parser.add_argument("--valor", default=None, help="red de valor (checkpoint) para puntuar las posiciones en la búsqueda")
    args = parser.parse_args()

    modo = f"red + búsqueda de profundidad {args.busqueda} (peso de la red {args.peso_red:g})" if args.busqueda > 0 else "red sola"
    print(f"\n== ELO de {Path(args.checkpoint).stem}, {modo} ({args.aperturas * 2} partidas por rival, {args.tiempo}s por jugada) ==")
    resultados = medir(args.checkpoint, args.elos, args.aperturas, args.tiempo, args.busqueda, args.peso_red, args.tiempo_busqueda, args.valor)
    estimacion, bajo, alto = estimar_elo(resultados)
    total = sum(m.partidas for _, m in resultados)
    todo_igual = all(m.victorias_a == 0 for _, m in resultados) or all(m.victorias_b == 0 for _, m in resultados)
    print(f"\nELO estimado: {estimacion:.0f}  (intervalo ~95 %: {bajo:.0f} a {alto:.0f}; {total} partidas)")
    if todo_igual and all(m.tablas == 0 for _, m in resultados):
        print("Aviso: sin ningún resultado mixto la estimación es solo una cota; probá rivales más débiles o más fuertes.")


if __name__ == "__main__":
    main()
