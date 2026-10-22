"""Mide qué tan bien reconocen los modelos actuales las posiciones completas guardadas, con la cámara principal, la secundaria y las dos.

Usa las capturas de posición completa de `training/dataset_propio_cuadros/` (cada una con su FEN etiquetado casilla por casilla) y las esquinas con
las que se tomaron, no la calibración de hoy. Para cada posición reconoce con cada cámara por separado y con las dos fusionadas (producto de las
probabilidades) y cuenta aciertos de ocupación (vacía / blanca / negra) y de tipo de pieza (sobre las casillas que de verdad tienen pieza).

Ojo: si las capturas ya se usaron para entrenar, el resultado es optimista. Para una medida honesta, capturá posiciones nuevas DESPUÉS de entrenar
y evaluá solo esas con `--desde` (el número de captura: el nombre del archivo `<id>.json`, que es la hora en milisegundos).

Uso:
    python3 -m training.evaluar_reconocimiento
    python3 -m training.evaluar_reconocimiento --desde 1761141000000
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

import cv2
import numpy as np

from backend.servicios.vision import ocupacion, piezas
from backend.servicios.vision.captura_estable import ocupacion_de_imagen
from backend.servicios.vision.fusion import fusionar_probabilidades
from backend.servicios.vision.jugada_probable import NOMBRES
from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.reconocimiento import recortes_de_imagen
from backend.servicios.vision.validacion_posicion import limitar_por_material

CASILLAS_POSICION_COMPLETA = 64


def puntuar(verdad: dict[str, str], probs_ocupacion: np.ndarray, probs_piezas: np.ndarray | None, clases_piezas: list[str] | None) -> dict[str, int]:
    """Aciertos de una posición: `{"ocupacion_ok", "ocupacion_total", "pieza_ok", "pieza_total", "exacta"}`.

    `verdad` es `{casilla: clase de las 13}`; las probabilidades van en el orden de `NOMBRES`. Los de pieza se cuentan solo sobre las casillas que
    tienen pieza de verdad (y quedan en 0 si no hay modelo de piezas). `exacta` es 1 si las 64 casillas tienen bien la ocupación.
    """
    reales = [verdad[n] for n in NOMBRES]
    vistas = probs_ocupacion.argmax(axis=1)
    ocupacion_ok = sum(ocupacion.CLASES_OCUPACION[v] == ocupacion.clase_a_ocupacion(r) for v, r in zip(vistas, reales))
    pieza_ok = pieza_total = 0
    if probs_piezas is not None and clases_piezas is not None:
        pedidas = probs_piezas.argmax(axis=1)
        for p, r in zip(pedidas, reales):
            if r != CLASE_VACIA:
                pieza_total += 1
                pieza_ok += clases_piezas[p] == r
    return {"ocupacion_ok": int(ocupacion_ok), "ocupacion_total": len(reales), "pieza_ok": int(pieza_ok), "pieza_total": pieza_total, "exacta": int(ocupacion_ok == len(reales))}


def _leer(cuadro: np.ndarray, datos: dict, camara: str) -> tuple[np.ndarray, np.ndarray | None]:
    """`(probabilidades de ocupación (64, 3), probabilidades de piezas (64, clases) o None sin modelo)` de una captura, con sus esquinas guardadas."""
    esquinas = np.array(datos["esquinas"], dtype=np.float32)
    probs_ocupacion = ocupacion_de_imagen(cuadro, camara, esquinas)
    try:
        recortes, _, _ = recortes_de_imagen(cuadro, camara, esquinas=esquinas)
        return probs_ocupacion, piezas.probabilidades([recortes[n] for n in NOMBRES])
    except FileNotFoundError:
        return probs_ocupacion, None


def _cargar_posiciones(desde: int) -> dict[str, dict[str, tuple[np.ndarray, dict]]]:
    """`{grupo: {camara: (cuadro, manifiesto)}}` de las capturas de posición completa con id >= `desde`."""
    from training.capturar_dataset_propio import carpeta_cuadros

    grupos: dict[str, dict[str, tuple[np.ndarray, dict]]] = defaultdict(dict)
    for manifiesto in sorted(carpeta_cuadros().glob("*.json")):
        if manifiesto.stem.isdigit() and int(manifiesto.stem) < desde:
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        if len(datos["etiquetas"]) < CASILLAS_POSICION_COMPLETA:
            continue  # captura de una sola pieza: no tiene el tablero entero etiquetado
        cuadro = cv2.imread(str(manifiesto.with_suffix(".jpg")))
        if cuadro is not None:
            grupos[datos.get("grupo", manifiesto.stem)][datos.get("camara", "principal")] = (cuadro, datos)
    return grupos


def evaluar(desde: int = 0) -> dict[str, dict[str, int]]:
    """Suma los aciertos por modo de cámara: `principal`, `secundaria` y `ambas` (esta última solo con las posiciones que tienen las dos)."""
    totales: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    clases_piezas = None
    try:
        clases_piezas = piezas.clases_del_modelo()
    except FileNotFoundError:
        pass
    for vistas in _cargar_posiciones(desde).values():
        lecturas = {camara: _leer(cuadro, datos, camara) for camara, (cuadro, datos) in vistas.items()}
        verdad = next(iter(vistas.values()))[1]["etiquetas"]
        modos = dict(lecturas)
        if len(lecturas) > 1:
            con_piezas = [p for _, p in lecturas.values() if p is not None]
            modos["ambas"] = (
                fusionar_probabilidades([o for o, _ in lecturas.values()]),
                fusionar_probabilidades(con_piezas) if len(con_piezas) == len(lecturas) else None,
            )
        for modo, (probs_o, probs_p) in modos.items():
            for clave, valor in puntuar(verdad, probs_o, probs_p, clases_piezas).items():
                totales[modo][clave] += valor
            if probs_p is not None and clases_piezas is not None:
                totales[modo]["pieza_ok_limitado"] += puntuar(verdad, probs_o, limitar_por_material(probs_p, clases_piezas), clases_piezas)["pieza_ok"]
            totales[modo]["posiciones"] += 1
    return {modo: dict(cuentas) for modo, cuentas in totales.items()}


def _porcentaje(ok: int, total: int) -> str:
    return f"{100 * ok / total:5.1f} %" if total else "    — "


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa el reconocimiento por modo de cámara")
    parser.add_argument("--desde", type=int, default=0, help="solo capturas con id (hora en ms) mayor o igual")
    resultados = evaluar(parser.parse_args().desde)
    if not resultados:
        print("No hay capturas de posición completa. Sacá algunas en «Entrenamiento de piezas» y volvé a correr esto.")
        return
    print("Modo        posiciones   ocupación   tipo de pieza   con límites de material   posiciones exactas")
    for modo in ("principal", "secundaria", "ambas"):
        c = resultados.get(modo)
        if c:
            print(
                f"{modo:<11} {c['posiciones']:>10}   {_porcentaje(c['ocupacion_ok'], c['ocupacion_total'])}"
                f"   {_porcentaje(c['pieza_ok'], c['pieza_total'])}        {_porcentaje(c.get('pieza_ok_limitado', 0), c['pieza_total'])}               {c['exacta']}/{c['posiciones']}"
            )
    print("\nSi estas capturas se usaron para entrenar, los números son optimistas: usá --desde con capturas nuevas.")


if __name__ == "__main__":
    main()
