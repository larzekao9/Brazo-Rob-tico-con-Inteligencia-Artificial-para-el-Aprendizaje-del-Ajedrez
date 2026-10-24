"""Arma el ZIP de fotos para entrenar en Colab (`training/colab_vision_piezas_2d_3d.ipynb`): la cámara principal en su posición actual + la secundaria de arriba.

De la principal entran las capturas tomadas con la cámara en su posición actual (esquinas a menos de 40 px de su calibración) y las casillas que corregiste en el probador; de la
secundaria, las que se ven desde arriba (más nítidas). Lleva los recortes 2D (`ampliado`) y 3D (`volumen`) y `metadatos.csv` con la cámara de cada foto.

Uso (desde la raíz del backend):
    python scripts/exportar_zip_colab.py
    python scripts/exportar_zip_colab.py --sin-secundaria      # solo la principal
    python scripts/exportar_zip_colab.py --todas-las-de-la-principal   # también las de antes de la última calibración
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.servicios.vision import dataset_propio  # noqa: E402
from training.entrenar_candidato import esquinas_actuales  # noqa: E402


def main() -> None:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--sin-secundaria", action="store_true", help="no incluir las fotos de la secundaria")
    analizador.add_argument("--todas-las-de-la-principal", action="store_true", help="incluir también las fotos de la principal tomadas con la cámara en otra posición")
    analizador.add_argument("--salida", type=Path, default=None, help="ruta del ZIP (por defecto training/exportaciones_colab/dataset_piezas_<fecha>.zip)")
    argumentos = analizador.parse_args()
    cerca = None if argumentos.todas_las_de_la_principal else esquinas_actuales("principal")
    destino = argumentos.salida or RAIZ / "training" / "exportaciones_colab" / f"dataset_piezas_{time.strftime('%Y%m%d_%H%M')}.zip"
    resumen = dataset_propio.exportar_zip_para_colab(destino, cerca_de=cerca, incluir_secundaria=not argumentos.sin_secundaria)
    print(f"ZIP: {resumen['ruta']} ({Path(resumen['ruta']).stat().st_size / 1e6:.0f} MB)")
    print(f"Recortes por cámara: {resumen['por_camara']}")
    print("Por clase (recortes 2D):")
    for clase, n in resumen["por_clase"].items():
        print(f"  {clase:14s} {n}")


if __name__ == "__main__":
    main()
