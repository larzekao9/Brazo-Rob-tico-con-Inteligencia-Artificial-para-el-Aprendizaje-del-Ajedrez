"""Datos para la cabeza de valor de Turing: posiciones con la evaluación de un motor fuerte, de la base de evaluaciones de Lichess.

La red de política dice QUÉ jugada prefiere; la cabeza de valor dice QUIÉN VA GANANDO en una posición. Para entrenarla hacen
falta posiciones con una evaluación confiable: la base de evaluaciones de Lichess (https://database.lichess.org/#evals,
`lichess_db_eval.jsonl.zst`, unos 22 GB) trae millones de posiciones analizadas por Stockfish a gran profundidad. Se usa
**solo como etiqueta de entrenamiento** (regla 1 del proyecto: la independencia aplica al jugar, no al entrenar).

No hace falta bajar todo el archivo: se lee en streaming y se corta al juntar las posiciones pedidas (con ~150 MB comprimidos
salen ~1,8 millones de posiciones). Cada línea es un JSON `{"fen": ..., "evals": [{"pvs": [{"cp"|"mate", "line"}], "depth"}]}`
y el `cp` está **desde la perspectiva de las blancas** (verificado contra Stockfish: coincide el signo en 60 de 60 posiciones).

Objetivo de entrenamiento: `v = tanh(cp / ESCALA_CP)` visto desde quien mueve (+1 = gana quien mueve, -1 = pierde, 0 = igualdad),
y ±1 para los mates. Es la misma perspectiva con la que la red de política mira el tablero.

Uso:
    python -m training.datos_valor --salida training/dataset_valor/valor_1m.npz --maximo 1000000
"""
from __future__ import annotations

import argparse
import io
import json
import math
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import chess
import numpy as np
import zstandard

from training.data_pipeline import board_to_tensor

URL_BASE_EVALUACIONES = "https://database.lichess.org/lichess_db_eval.jsonl.zst"
ESCALA_CP = 400.0
"""`v = tanh(cp / ESCALA_CP)`: 400 cp (unos 4 peones) ya es una ventaja decisiva (v ≈ 0,76)."""
PROFUNDIDAD_MINIMA = 20
"""Se descartan evaluaciones de menos profundidad: son las menos confiables."""
CP_MAXIMO = 3000


def objetivo_valor(cp_blancas: int | None, mate_blancas: int | None, blancas_mueven: bool) -> float:
    """Valor en [-1, 1] desde quien mueve, a partir de la evaluación (siempre dada desde las blancas).

    Con `mate_blancas` (positivo: dan mate las blancas, negativo: las negras) el valor es ±1.
    """
    if mate_blancas is not None:
        valor_blancas = 1.0 if mate_blancas > 0 else -1.0
    elif cp_blancas is not None:
        valor_blancas = math.tanh(max(-CP_MAXIMO, min(CP_MAXIMO, cp_blancas)) / ESCALA_CP)
    else:
        raise ValueError("Hace falta cp o mate")
    return valor_blancas if blancas_mueven else -valor_blancas


def cp_desde_valor(valor: float) -> float:
    """Inverso de `objetivo_valor` para el cp: centipeones desde quien mueve (acotado a ±CP_MAXIMO)."""
    valor = max(-0.9999, min(0.9999, valor))
    return max(-CP_MAXIMO, min(CP_MAXIMO, ESCALA_CP * math.atanh(valor)))


def leer_evaluaciones(origen: str | Path = URL_BASE_EVALUACIONES, profundidad_minima: int = PROFUNDIDAD_MINIMA) -> Iterator[tuple[str, float]]:
    """Recorre la base de evaluaciones y devuelve `(fen_completo, valor_de_quien_mueve)` por posición.

    `origen` es una URL (se baja en streaming por rangos) o un `.jsonl.zst` local. Salta las líneas mal formadas y las de menos
    de `profundidad_minima`; de cada posición toma la evaluación de mayor profundidad y su mejor línea.
    """
    flujo, cerrar = _abrir(origen)
    try:
        lector = zstandard.ZstdDecompressor().stream_reader(flujo)
        resto = b""
        while True:
            try:
                trozo = lector.read(1 << 20)
            except zstandard.ZstdError:  # el rango pedido termina a mitad de un bloque: fin de los datos disponibles
                return
            if not trozo:
                return
            *lineas, resto = (resto + trozo).split(b"\n")
            for linea in lineas:
                fila = _procesar_linea(linea, profundidad_minima)
                if fila is not None:
                    yield fila
    finally:
        cerrar()


def _procesar_linea(linea: bytes, profundidad_minima: int) -> tuple[str, float] | None:
    try:
        registro = json.loads(linea)
        mejor = max(registro["evals"], key=lambda e: e["depth"])
        if mejor["depth"] < profundidad_minima:
            return None
        linea_principal = mejor["pvs"][0]
        fen = registro["fen"] + " 0 1"  # la base no trae los contadores de jugadas
        blancas_mueven = fen.split()[1] == "w"
        valor = objetivo_valor(linea_principal.get("cp"), linea_principal.get("mate"), blancas_mueven)
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    return fen, valor


def _abrir(origen: str | Path):
    """Devuelve `(flujo_de_bytes, función_para_cerrar)`; para una URL pide el archivo por tramos de 64 MB."""
    if str(origen).startswith(("http://", "https://")):
        flujo = _FlujoPorRangos(str(origen))
        return flujo, lambda: None
    archivo = open(origen, "rb")
    return archivo, archivo.close


class _FlujoPorRangos(io.RawIOBase):
    """Lee una URL por pedidos con `Range` de `TRAMO` bytes (sirviendo lecturas chicas desde un buffer), para poder cortar la
    descarga apenas ya hay suficientes posiciones."""

    TRAMO = 32 * 1024 * 1024

    def __init__(self, url: str) -> None:
        self.url, self.posicion, self.fin, self._buffer = url, 0, False, b""

    def readable(self) -> bool:
        return True

    def _pedir_tramo(self) -> bytes:
        solicitud = urllib.request.Request(self.url, headers={"Range": f"bytes={self.posicion}-{self.posicion + self.TRAMO - 1}"})
        try:
            with urllib.request.urlopen(solicitud, timeout=120) as respuesta:
                return respuesta.read()
        except urllib.error.HTTPError as error:
            if error.code == 416:  # se pasó del final del archivo
                return b""
            raise

    def readinto(self, destino) -> int:
        if not self._buffer and not self.fin:
            self._buffer = self._pedir_tramo()
            self.posicion += len(self._buffer)
            self.fin = not self._buffer
        entregado = self._buffer[: len(destino)]
        destino[: len(entregado)] = entregado
        self._buffer = self._buffer[len(entregado):]
        return len(entregado)


def construir_dataset(origen: str | Path, salida: str | Path, maximo: int, salto: int = 1) -> int:
    """Guarda hasta `maximo` posiciones en un `.npz`: `posiciones` (N, 8, 8, 12) en `uint8` y `valores` (N,) en `float32`.

    `salto` toma una de cada `salto` posiciones, para repartir la muestra en más archivo cuando se lee un tramo largo.
    Devuelve cuántas posiciones guardó.
    """
    posiciones: list[np.ndarray] = []
    valores: list[float] = []
    for indice, (fen, valor) in enumerate(leer_evaluaciones(origen)):
        if indice % salto:
            continue
        try:
            tablero = chess.Board(fen)
        except ValueError:
            continue
        posiciones.append(board_to_tensor(tablero).astype(np.uint8))
        valores.append(valor)
        if len(valores) >= maximo:
            break
    if not valores:
        raise RuntimeError("No se leyó ninguna posición: revisá el origen y la conexión")
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(salida, posiciones=np.stack(posiciones), valores=np.asarray(valores, dtype=np.float32))
    return len(valores)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--origen", default=URL_BASE_EVALUACIONES, help="URL o archivo .jsonl.zst de evaluaciones")
    parser.add_argument("--salida", default="training/dataset_valor/valor.npz")
    parser.add_argument("--maximo", type=int, default=1_000_000)
    parser.add_argument("--salto", type=int, default=1, help="tomar una de cada N posiciones")
    args = parser.parse_args()
    cantidad = construir_dataset(args.origen, args.salida, args.maximo, args.salto)
    print(f"Guardadas {cantidad} posiciones en {args.salida}")


if __name__ == "__main__":
    main()
