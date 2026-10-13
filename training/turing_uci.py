"""Turing como motor UCI: el protocolo estándar con el que los programas de ajedrez hablan con sus motores.

Con esta interfaz, Turing se puede conectar a cualquier programa que acepte motores UCI (Arena, Cute Chess, Lichess-bot,
`python-chess`, etc.), igual que Stockfish. Turing decide solo: red neuronal + filtro táctico (`predecir_jugada_maestra`),
sin consultar a Stockfish (regla 1 de `CLAUDE.md`).

Uso desde una terminal (queda esperando comandos UCI por la entrada estándar):

    python -m training.turing_uci --checkpoint training/checkpoints/modelo_jugadas_v6_2026-10-12.pt

Para un programa de ajedrez con interfaz gráfica, usar `training/turing_uci.bat` como ruta del motor.

Comandos soportados: `uci`, `isready`, `setoption`, `ucinewgame`, `position`, `go` (ignora los tiempos: responde de
inmediato), `stop`, `quit`. Opciones: `Checkpoint` (ruta del `.pt`) y `Nivel` (0 a 18; con 18 juega a su máxima fuerza).
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import chess

NOMBRE = "Turing"
AUTORES = "Suarez Burgos Hebert y Arze Kao Luis Angel"
NIVEL_MAXIMO = 18


class MotorUCI:
    """Estado de una sesión UCI. `procesar` recibe una línea y devuelve las líneas de respuesta (pura, fácil de probar).

    `decidir` es la función `(fen, nivel) -> jugada en SAN`; por defecto es el modelo real. Se puede inyectar otra para
    probar el protocolo sin cargar la red.
    """

    def __init__(
        self,
        ruta_checkpoint: str | Path | None = None,
        nivel: int = NIVEL_MAXIMO,
        decidir: Callable[[str, int], str] | None = None,
    ) -> None:
        self.ruta_checkpoint = str(ruta_checkpoint) if ruta_checkpoint else None
        self.nivel = nivel
        self._decidir = decidir
        self.tablero = chess.Board()
        self.terminado = False

    # -- decisión -----------------------------------------------------------------------------------------------
    def _decidir_con_modelo(self, fen: str, nivel: int) -> str:
        from backend.servicios.aprendizaje.inferencia import RUTA_CHECKPOINT_POR_DEFECTO, predecir_jugada_maestra

        ruta = self.ruta_checkpoint or RUTA_CHECKPOINT_POR_DEFECTO
        return predecir_jugada_maestra(fen, ruta_checkpoint=ruta, nivel=None if nivel >= NIVEL_MAXIMO else nivel)

    def elegir_jugada(self) -> str:
        """Jugada en formato UCI (`e2e4`) para la posición actual, o `0000` si no hay jugadas legales."""
        if not any(self.tablero.legal_moves):
            return "0000"
        decidir = self._decidir or self._decidir_con_modelo
        san = decidir(self.tablero.fen(), self.nivel)
        return self.tablero.parse_san(san).uci()

    # -- protocolo ----------------------------------------------------------------------------------------------
    def procesar(self, linea: str) -> list[str]:
        partes = linea.strip().split()
        if not partes:
            return []
        comando, resto = partes[0], partes[1:]
        if comando == "uci":
            return [
                f"id name {NOMBRE}",
                f"id author {AUTORES}",
                f"option name Checkpoint type string default {self.ruta_checkpoint or '<por defecto>'}",
                f"option name Nivel type spin default {NIVEL_MAXIMO} min 0 max {NIVEL_MAXIMO}",
                "uciok",
            ]
        if comando == "isready":
            return ["readyok"]
        if comando == "setoption":
            return self._setoption(resto)
        if comando == "ucinewgame":
            self.tablero = chess.Board()
            return []
        if comando == "position":
            return self._position(resto)
        if comando == "go":
            return self._go()
        if comando == "quit":
            self.terminado = True
        return []  # `stop`, `debug`, `register`, comandos desconocidos: se ignoran como pide el protocolo

    def _setoption(self, resto: list[str]) -> list[str]:
        # setoption name <nombre> [value <valor>]; el nombre y el valor pueden tener espacios.
        if "name" not in resto:
            return []
        inicio = resto.index("name") + 1
        fin = resto.index("value") if "value" in resto else len(resto)
        nombre = " ".join(resto[inicio:fin]).lower()
        valor = " ".join(resto[fin + 1:]) if "value" in resto else ""
        if nombre == "checkpoint" and valor:
            self.ruta_checkpoint = valor
        elif nombre == "nivel" and valor.lstrip("-").isdigit():
            self.nivel = max(0, min(NIVEL_MAXIMO, int(valor)))
        return []

    def _position(self, resto: list[str]) -> list[str]:
        if not resto:
            return []
        if resto[0] == "startpos":
            tablero, siguiente = chess.Board(), 1
        elif resto[0] == "fen":
            fin = resto.index("moves") if "moves" in resto else len(resto)
            try:
                tablero = chess.Board(" ".join(resto[1:fin]))
            except ValueError:
                return ["info string FEN invalido"]
            siguiente = fin
        else:
            return []
        if siguiente < len(resto) and resto[siguiente] == "moves":
            for uci in resto[siguiente + 1:]:
                try:
                    tablero.push_uci(uci)
                except ValueError:
                    return [f"info string jugada ilegal en position: {uci}"]
        self.tablero = tablero
        return []

    def _go(self) -> list[str]:
        try:
            return [f"bestmove {self.elegir_jugada()}"]
        except Exception as error:  # el motor nunca debe caerse en mitad de una partida
            alternativa = next(iter(self.tablero.legal_moves), None)
            return [
                f"info string error del modelo: {type(error).__name__}: {error}",
                f"bestmove {alternativa.uci() if alternativa else '0000'}",
            ]


def ejecutar(entrada, salida, motor: MotorUCI) -> None:
    """Bucle principal: lee comandos de `entrada` y escribe las respuestas en `salida` hasta `quit` o fin de entrada."""
    for linea in entrada:
        for respuesta in motor.procesar(linea):
            salida.write(respuesta + "\n")
        salida.flush()
        if motor.terminado:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Turing como motor UCI")
    parser.add_argument("--checkpoint", help="ruta del modelo .pt (por defecto, el último de training/checkpoints)")
    parser.add_argument("--nivel", type=int, default=NIVEL_MAXIMO, help="0 a 18; 18 = máxima fuerza")
    args = parser.parse_args()
    ejecutar(sys.stdin, sys.stdout, MotorUCI(args.checkpoint, args.nivel))


if __name__ == "__main__":
    main()
