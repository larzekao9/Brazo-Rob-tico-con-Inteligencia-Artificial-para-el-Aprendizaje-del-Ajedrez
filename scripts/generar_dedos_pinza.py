"""Genera el STL de un taco (dedo) largo para la pinza DH PGE-50-26: el taco negro de fábrica, más largo y un poco más delgado.

Se corre con Blender, sin ventana:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P scripts/generar_dedos_pinza.py -- ^
        --salida dedo_largo.stl            (con las medidas de partida, que son ESTIMADAS: ver abajo)

Cómo es el taco de fábrica y qué cambia
    El taco se atornilla por ABAJO con un tornillo M3 corto: la cabeza queda hundida en una muesca redonda de la cara de abajo, el
    tornillo atraviesa una pared de 4,5 mm y rosca unos 3 mm en la pieza plateada de la mordaza (medido con el taco impreso: con una pared
    de 3 mm sobresalían 4,5 mm de rosca, que era demasiado).
    El dedo nuevo es lo mismo pero más largo (`--extension`, 40 mm): la muesca de la cabeza se alarga con las paredes, de modo que el
    tornillo sigue siendo el de 10 mm y queda en el mismo lugar respecto de la mordaza; la llave Allen entra por la muesca larga.
    Además es más delgado (`--adelgazar`): el material se quita de la cara de AFUERA, así la cara de adentro (la que toca la pieza)
    no se mueve y se conserva el recorrido de apertura.

Medidas de partida (ESTIMADAS, hay que confirmarlas con el taco de fábrica antes de imprimir los dedos largos)
    grosor 13 mm (del manual de DH: es el espesor de la pieza que toca la pieza de ajedrez), ancho 14 mm y largo 13 mm (estimados de
    las fotos). Con `--extension 0` sale una réplica corta del taco: imprimila primero para comprobar que encaja.

Con `--acostado` el STL sale ya girado para imprimirlo recostado sobre una cara de Y: las capas corren a lo largo del dedo (mucho más
resistente a la flexión que parado), imprime más rápido y no necesita borde. Como el canal de la muesca queda horizontal, se hace en forma
de GOTA (círculo con la punta hacia arriba) para que se imprima sin soportes ni combarse.

Ejes (mm): X = sentido en que se abren y cierran los dedos (el grosor; X = 0 es la cara de adentro), Y = ancho, Z = largo, con el
origen en la cara de arriba (la que apoya en la mordaza) y el dedo creciendo hacia abajo.
Imprimir acostado (sobre una cara de Y) para que las capas corran a lo largo del dedo.
"""
from __future__ import annotations

import argparse
import math
import sys

import bmesh
import bpy
import mathutils

DIAMETRO_PASO_M3 = 4.4
"""Agujero de paso del tornillo: 4,4 mm (antes 3,4: el tornillo no pasaba en el taco impreso; la impresión 3D cierra los agujeros chicos)."""
DIAMETRO_MUESCA_M3 = 6.2
PARED_SUPERIOR = 4.5
"""Pared de arriba por donde pasa el cuerpo del tornillo. Con 3 mm el tornillo sobresalía unos 4,5 mm de la cara de arriba y entraba
demasiado en la mordaza (la rosca de la pieza plateada es de 4 mm de profundidad); con 4,5 mm sobresalen unos 3 mm."""
PARED_MINIMA = 1.6
"""Pared mínima alrededor de la muesca, para que imprima bien."""


def _argumentos() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--grosor", type=float, default=13.0, help="grosor (X) del taco de fábrica")
    p.add_argument("--ancho", type=float, default=14.0, help="ancho (Y) del taco de fábrica")
    p.add_argument("--largo", type=float, default=13.0, help="largo (Z) del taco de fábrica")
    p.add_argument("--centro-x", type=float, default=None, help="posición X del tornillo desde la cara de adentro (por defecto, el centro del grosor de fábrica)")
    p.add_argument("--extension", type=float, default=40.0, help="cuánto más largo que el de fábrica")
    p.add_argument("--pared-superior", type=float, default=PARED_SUPERIOR,
                   help="pared de arriba por donde pasa el tornillo = 10 (tornillo) - 3 (cabeza) - lo que sobresale la rosca por arriba")
    p.add_argument("--adelgazar", type=float, default=1.5, help="mm menos de grosor, quitados de la cara de afuera")
    p.add_argument("--rebaje-goma", type=float, default=0.8, help="profundidad del rebaje para la goma en la cara de adentro (0 = sin rebaje)")
    p.add_argument("--acostado", action="store_true", help="canal en forma de gota y STL girado para imprimir recostado")
    p.add_argument("--salida", required=True)
    return p.parse_args(argv)


def _validar(a: argparse.Namespace) -> tuple[float, float]:
    centro_x = a.centro_x if a.centro_x is not None else a.grosor / 2
    grosor = a.grosor - a.adelgazar
    pared_afuera = grosor - (centro_x + DIAMETRO_MUESCA_M3 / 2)
    if pared_afuera < PARED_MINIMA:
        raise SystemExit(
            f"Con {grosor:.1f} mm de grosor queda una pared de {pared_afuera:.1f} mm detrás de la muesca (mínimo {PARED_MINIMA} mm): "
            f"adelgazá menos (máximo {a.adelgazar - (PARED_MINIMA - pared_afuera):.1f} mm)"
        )
    pared_lado = (a.ancho - DIAMETRO_MUESCA_M3) / 2
    if pared_lado < PARED_MINIMA:
        raise SystemExit(f"Con {a.ancho:.1f} mm de ancho queda una pared de {pared_lado:.1f} mm al costado de la muesca (mínimo {PARED_MINIMA} mm)")
    if centro_x - DIAMETRO_MUESCA_M3 / 2 < PARED_MINIMA + (a.rebaje_goma if a.rebaje_goma > 0 else 0):
        raise SystemExit("El tornillo queda demasiado cerca de la cara de adentro para dejar pared y rebaje de la goma")
    return centro_x, grosor


def _caja(nombre: str, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
    malla = bpy.data.meshes.new(nombre)
    objeto = bpy.data.objects.new(nombre, malla)
    bpy.context.collection.objects.link(objeto)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x, v.co.y, v.co.z = (x0 if v.co.x < 0 else x1), (y0 if v.co.y < 0 else y1), (z0 if v.co.z < 0 else z1)
    bm.to_mesh(malla)
    bm.free()
    return objeto


def _cilindro_z(nombre: str, diametro: float, z0: float, z1: float, x: float, y: float):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=diametro / 2, radius2=diametro / 2, depth=z1 - z0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, (z0 + z1) / 2))
    malla = bpy.data.meshes.new(nombre)
    bm.to_mesh(malla)
    bm.free()
    objeto = bpy.data.objects.new(nombre, malla)
    bpy.context.collection.objects.link(objeto)
    return objeto


def _gota_z(nombre: str, diametro: float, z0: float, z1: float, x: float, y: float):
    """Prisma a lo largo de Z con sección en gota: un círculo con la punta hacia +Y (sin voladizos mayores a 45° al imprimir recostado)."""
    r = diametro / 2
    puntos = [(x + r * math.cos(math.radians(45)), y + r * math.sin(math.radians(45))), (x, y + r * math.sqrt(2)),
              (x + r * math.cos(math.radians(135)), y + r * math.sin(math.radians(135)))]
    for grados in range(135 + 5, 405, 5):
        puntos.append((x + r * math.cos(math.radians(grados)), y + r * math.sin(math.radians(grados))))
    bm = bmesh.new()
    cara = bm.faces.new([bm.verts.new((px, py, z0)) for px, py in puntos])
    extruido = bmesh.ops.extrude_face_region(bm, geom=[cara])
    bmesh.ops.translate(bm, verts=[e for e in extruido["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, z1 - z0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    malla = bpy.data.meshes.new(nombre)
    bm.to_mesh(malla)
    bm.free()
    objeto = bpy.data.objects.new(nombre, malla)
    bpy.context.collection.objects.link(objeto)
    return objeto


def _restar(cuerpo, herramienta) -> None:
    modificador = cuerpo.modifiers.new("restar", "BOOLEAN")
    modificador.operation, modificador.solver, modificador.object = "DIFFERENCE", "EXACT", herramienta
    bpy.context.view_layer.objects.active = cuerpo
    bpy.ops.object.modifier_apply(modifier=modificador.name)
    bpy.data.objects.remove(herramienta, do_unlink=True)


def construir(a: argparse.Namespace):
    centro_x, grosor = _validar(a)
    largo_total = a.largo + a.extension
    if a.pared_superior < PARED_MINIMA or a.pared_superior > a.largo - 3.0:
        raise SystemExit(f"La pared de arriba ({a.pared_superior} mm) tiene que estar entre {PARED_MINIMA} mm y {a.largo - 3.0:.1f} mm")
    y_centro = a.ancho / 2
    dedo = _caja("dedo", 0.0, grosor, 0.0, a.ancho, -largo_total, 0.0)
    # Agujero de paso del tornillo (pared de arriba) y muesca de la cabeza, que llega hasta el extremo de abajo: es la muesca alargada.
    perforar = _gota_z if a.acostado else _cilindro_z
    _restar(dedo, perforar("paso", DIAMETRO_PASO_M3, -a.pared_superior - 0.01, 1.0, centro_x, y_centro))
    _restar(dedo, perforar("muesca", DIAMETRO_MUESCA_M3, -largo_total - 1.0, -a.pared_superior, centro_x, y_centro))
    # Rebaje poco profundo en la cara de adentro para pegar la goma fina, solo en el tramo largo.
    if a.rebaje_goma > 0 and a.extension > 8:
        _restar(dedo, _caja("goma", -1.0, a.rebaje_goma, 2.0, a.ancho - 2.0, -largo_total + 1.0, -a.largo - 2.0))
    return dedo


def main() -> None:
    argumentos = _argumentos()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dedo = construir(argumentos)
    if argumentos.acostado:  # Y pasa a ser la altura de impresión: el dedo queda recostado sobre su cara Y = 0
        dedo.rotation_euler = (math.radians(90), 0, 0)
        bpy.context.view_layer.objects.active = dedo
        dedo.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.ops.object.select_all(action="DESELECT")
    dedo.select_set(True)
    bpy.context.view_layer.objects.active = dedo
    bpy.ops.wm.stl_export(filepath=argumentos.salida, export_selected_objects=True)
    print(f"STL guardado en {argumentos.salida}")


if __name__ == "__main__":
    main()
