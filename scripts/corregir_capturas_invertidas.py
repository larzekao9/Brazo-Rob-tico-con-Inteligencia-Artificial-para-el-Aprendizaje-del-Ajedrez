"""Busca en el dataset de piezas las capturas hechas con la calibración girada 180° (blancas y negras al revés) y las corrige.

Uso (desde la raíz del repo):
    python -m scripts.corregir_capturas_invertidas            # solo lista las capturas invertidas
    python -m scripts.corregir_capturas_invertidas --aplicar  # gira sus esquinas y vuelve a recortar

Ver `training.capturar_dataset_propio.corregir_capturas_invertidas`.
"""
from __future__ import annotations

import sys

from training.capturar_dataset_propio import corregir_capturas_invertidas


def main(argumentos: list[str]) -> int:
    aplicar = "--aplicar" in argumentos
    invertidas = corregir_capturas_invertidas(aplicar=aplicar)
    if not invertidas:
        print("No hay capturas invertidas.")
        return 0
    for entrada in invertidas:
        estado = "corregida" if entrada["corregida"] else "invertida"
        print(
            f"{entrada['captura']} ({entrada['camara']}): {estado} — brillo de las 'blancas' {entrada['brillo_blancas']}, "
            f"de las 'negras' {entrada['brillo_negras']}"
        )
    if not aplicar:
        print(f"\n{len(invertidas)} capturas invertidas. Correr con --aplicar para corregirlas.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
