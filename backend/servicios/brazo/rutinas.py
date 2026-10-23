"""Rutinas del brazo: listas de pasos con nombre, guardadas en `calibracion_local/rutinas/<nombre>.json`.

Una rutina se arma en el front moviendo el brazo virtual, se prueba en el emulador y después se llama por su nombre en el brazo real.
Tipos de paso: `articulaciones` (los 6 ángulos y la velocidad), `pinza` (apertura, y opcionalmente fuerza y velocidad), `esperar` (segundos)
y `rutina` (llama a otra, así se componen). Este módulo solo guarda y valida; quien ejecuta es `control_brazo.ejecutar_rutina`.

Seguridad: cada pose se valida con `geometria_brazo` (límites de articulación, mesa, tablero y choques entre eslabones), igual que el camino
en línea recta entre dos poses seguidas; un salto grande entre dos poses se rechaza (hay que poner una pose intermedia) y una rutina solo se acepta
para el brazo real si ya corrió completa en el emulador con exactamente esos pasos (`huella`).

Hay rutinas incorporadas (`INCORPORADAS`) que no se guardan en un archivo ni se pueden editar: «posición inicial» sale de la calibración del brazo.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from backend.servicios.brazo import geometria_brazo
from backend.servicios.brazo.calibracion_brazo import ARCHIVO_CALIBRACION_BRAZO, cargar_calibracion_brazo, cargar_parametros_agarre

DIRECTORIO = Path(ARCHIVO_CALIBRACION_BRAZO).parent / "rutinas"
LIMITES_ARTICULACIONES = geometria_brazo.LIMITES_ARTICULACIONES
INCORPORADAS = ("posición inicial",)
SALTO_MAXIMO_GRADOS = 150
PROFUNDIDAD_MAXIMA = 5
MAXIMO_PASOS = 200
_NOMBRE = re.compile(r"^[\w][\w \-]{0,39}$")


class ErrorRutina(Exception):
    """Error al guardar o leer una rutina, con un código tipo HTTP (404 no existe, 409 estado incorrecto, 422 dato inválido)."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo, self.mensaje = codigo, mensaje


def z_tope_guardado_mm() -> float | None:
    """La altura del tablero (`z_tope`) guardada en la calibración del brazo, o `None` si todavía no se midió."""
    try:
        parametros = cargar_parametros_agarre()
    except ValueError:
        return None
    return parametros.z_tope if parametros else None


def largo_pinza_guardado_m() -> float:
    """El largo de la pinza (brida a punta de los dedos) guardado en la calibración, en metros; si no hay, el que se supone por defecto."""
    try:
        parametros = cargar_parametros_agarre()
    except ValueError:
        parametros = None
    return parametros.largo_pinza_mm / 1000 if parametros else geometria_brazo.LARGO_PINZA_DEFECTO


def _angulos_cero() -> list[float] | None:
    """Los ángulos de la posición inicial (la «posición cero» calibrada del brazo), o `None` si no hay calibración."""
    try:
        calibracion = cargar_calibracion_brazo()
    except ValueError:
        return None
    return list(calibracion.angulos_cero) if calibracion else None


def _incorporada(nombre: str) -> dict | None:
    if nombre == "posición inicial" and (angulos := _angulos_cero()):
        return {"pasos": [{"tipo": "articulaciones", "angulos": angulos, "velocidad": 20}], "actualizada": None}
    return None


def _ruta(nombre: str) -> Path:
    if not isinstance(nombre, str) or not _NOMBRE.match(nombre):
        raise ErrorRutina(422, "El nombre debe tener de 1 a 40 letras, números, espacios, guiones o guiones bajos")
    return DIRECTORIO / f"{nombre}.json"


def _numero(valor, minimo: float, maximo: float, que: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not minimo <= valor <= maximo:
        raise ErrorRutina(422, f"{que} debe estar entre {minimo} y {maximo}")
    return float(valor)


def validar_paso(paso: dict, indice: int) -> dict:
    """Paso limpio (solo los campos que corresponden) o `ErrorRutina` si algo está fuera de rango."""
    donde = f"Paso {indice}"
    if not isinstance(paso, dict):
        raise ErrorRutina(422, f"{donde}: formato inválido")
    tipo = paso.get("tipo")
    if tipo == "articulaciones":
        angulos = paso.get("angulos")
        if not isinstance(angulos, list) or len(angulos) != 6:
            raise ErrorRutina(422, f"{donde}: hacen falta los 6 ángulos J1 a J6")
        limpio = {"tipo": tipo, "angulos": [_numero(a, *limite, f"{donde}: J{i}") for i, (a, limite) in enumerate(zip(angulos, LIMITES_ARTICULACIONES), start=1)]}
        limpio["velocidad"] = int(_numero(paso.get("velocidad", 20), 1, 100, f"{donde}: la velocidad"))
        if problemas := geometria_brazo.problemas_de_pose(limpio["angulos"], z_tope_guardado_mm(), largo_pinza_guardado_m()):
            raise ErrorRutina(422, f"{donde}: pose imposible: {'; '.join(problemas[:2])}")
        return limpio
    if tipo == "pinza":
        limpio = {"tipo": tipo, "apertura": int(_numero(paso.get("apertura"), 0, 1000, f"{donde}: la apertura"))}
        for campo, minimo, maximo in (("fuerza", 20, 100), ("velocidad", 1, 100)):
            if paso.get(campo) is not None:
                limpio[campo] = int(_numero(paso[campo], minimo, maximo, f"{donde}: {campo}"))
        return limpio
    if tipo == "esperar":
        return {"tipo": tipo, "segundos": _numero(paso.get("segundos"), 0, 30, f"{donde}: la espera")}
    if tipo == "rutina":
        _ruta(paso.get("nombre"))  # valida el nombre
        return {"tipo": tipo, "nombre": paso["nombre"]}
    raise ErrorRutina(422, f"{donde}: tipo desconocido (articulaciones, pinza, esperar o rutina)")


def aplanar(pasos: list[dict], _profundidad: int = 0, _en_curso: tuple[str, ...] = ()) -> list[dict]:
    """Los pasos con cada `rutina` reemplazada por los suyos, recursivamente (solo quedan articulaciones, pinza y esperar).

    Raises:
        ErrorRutina: llama a una rutina que no existe, hay un ciclo (A llama a B que llama a A) o la anidación pasa de `PROFUNDIDAD_MAXIMA`.
    """
    if _profundidad > PROFUNDIDAD_MAXIMA:
        raise ErrorRutina(422, f"Demasiadas rutinas anidadas (máximo {PROFUNDIDAD_MAXIMA})")
    planos: list[dict] = []
    for paso in pasos:
        if paso["tipo"] != "rutina":
            planos.append(paso)
            continue
        if paso["nombre"] in _en_curso:
            raise ErrorRutina(422, f"La rutina «{paso['nombre']}» se llama a sí misma ({' → '.join((*_en_curso, paso['nombre']))})")
        planos.extend(aplanar(_leer(paso["nombre"])["pasos"], _profundidad + 1, (*_en_curso, paso["nombre"])))
    return planos


def revisar_saltos(planos: list[dict]) -> None:
    """Rechaza dos poses seguidas que difieran en alguna articulación más de `SALTO_MAXIMO_GRADOS`."""
    anterior = None
    for numero, paso in enumerate(planos, start=1):
        if paso["tipo"] != "articulaciones":
            continue
        if anterior is not None:
            for j, (a, b) in enumerate(zip(anterior, paso["angulos"]), start=1):
                if abs(a - b) > SALTO_MAXIMO_GRADOS:
                    raise ErrorRutina(422, f"J{j} salta {abs(a - b):.0f}° entre dos poses seguidas (máximo {SALTO_MAXIMO_GRADOS}°): agregá una pose intermedia")
        anterior = paso["angulos"]


def revisar_trayectorias(planos: list[dict]) -> None:
    """Rechaza dos poses seguidas cuyo camino recto en articulaciones (el de `MovJ`) pase por una pose imposible (mesa, tablero o choque)."""
    anterior, numero_anterior = None, 0
    for numero, paso in enumerate(planos, start=1):
        if paso["tipo"] != "articulaciones":
            continue
        if anterior is not None and (problemas := geometria_brazo.problemas_de_trayectoria(anterior, paso["angulos"], z_tope_guardado_mm(), largo_pinza_guardado_m())):
            raise ErrorRutina(422, f"Entre el paso {numero_anterior} y el {numero} el brazo pasaría por una pose imposible: {problemas[0]}. Agregá una pose intermedia que lo rodee")
        anterior, numero_anterior = paso["angulos"], numero


def huella(planos: list[dict]) -> str:
    """Identifica exactamente qué hace una rutina (sus pasos ya aplanados): si cambia algo, cambia la huella y deja de estar validada."""
    return hashlib.sha256(json.dumps(planos, sort_keys=True).encode()).hexdigest()[:16]


def _leer(nombre: str) -> dict:
    if (incorporada := _incorporada(nombre)) is not None:
        return incorporada
    ruta = _ruta(nombre)
    if not ruta.exists():
        raise ErrorRutina(404, f"No existe la rutina «{nombre}»")
    return json.loads(ruta.read_text(encoding="utf-8"))


def obtener(nombre: str) -> dict:
    """`{"nombre", "pasos", "validada", "actualizada"}`; `validada` es `True` si corrió completa en el emulador con estos mismos pasos."""
    datos = _leer(nombre)
    incorporada = nombre in INCORPORADAS
    try:
        al_dia = incorporada or datos.get("huella_validada") == huella(aplanar(datos["pasos"], _en_curso=(nombre,)))
    except ErrorRutina:
        al_dia = False  # llama a una rutina que ya no existe
    return {"nombre": nombre, "pasos": datos["pasos"], "validada": al_dia, "actualizada": datos.get("actualizada"), "incorporada": incorporada}


def listar() -> list[dict]:
    """Las rutinas guardadas, por nombre: `{"nombre", "pasos" (cantidad), "validada", "actualizada"}`."""
    resumen = [
        {"nombre": n, "pasos": len(r["pasos"]), "validada": True, "actualizada": None, "incorporada": True}
        for n in INCORPORADAS
        if (r := _incorporada(n)) is not None
    ]
    if not DIRECTORIO.exists():
        return resumen
    for archivo in sorted(DIRECTORIO.glob("*.json")):
        try:
            rutina = obtener(archivo.stem)
        except (ErrorRutina, json.JSONDecodeError):
            continue
        resumen.append({"nombre": rutina["nombre"], "pasos": len(rutina["pasos"]), "validada": rutina["validada"], "actualizada": rutina["actualizada"], "incorporada": False})
    return resumen


def guardar(nombre: str, pasos: list[dict]) -> dict:
    """Valida y guarda `pasos` como la rutina `nombre` (la reemplaza si existe; deja de estar validada para el brazo real)."""
    ruta = _ruta(nombre)
    if nombre in INCORPORADAS:
        raise ErrorRutina(409, f"«{nombre}» es una rutina incorporada y no se puede cambiar: guardá una copia con otro nombre")
    if not isinstance(pasos, list) or not pasos:
        raise ErrorRutina(422, "La rutina necesita al menos un paso")
    if len(pasos) > MAXIMO_PASOS:
        raise ErrorRutina(422, f"Máximo {MAXIMO_PASOS} pasos por rutina")
    limpios = [validar_paso(p, i) for i, p in enumerate(pasos, start=1)]
    planos = aplanar(limpios, _en_curso=(nombre,))
    revisar_saltos(planos)
    revisar_trayectorias(planos)
    DIRECTORIO.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"pasos": limpios, "actualizada": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False, indent=1), encoding="utf-8")
    return obtener(nombre)


def borrar(nombre: str) -> None:
    """Borra la rutina. Si otra la llama, esa queda sin validar (y no se podrá ejecutar hasta arreglarla)."""
    ruta = _ruta(nombre)
    if nombre in INCORPORADAS:
        raise ErrorRutina(409, f"«{nombre}» es una rutina incorporada y no se puede borrar")
    if not ruta.exists():
        raise ErrorRutina(404, f"No existe la rutina «{nombre}»")
    ruta.unlink()


def pasos_para_ejecutar(nombre: str) -> tuple[list[dict], str]:
    """`(pasos aplanados, huella)` listos para correr: ya revisados (rangos, ciclos y saltos entre poses)."""
    rutina = _leer(nombre)
    planos = aplanar(rutina["pasos"], _en_curso=(nombre,))
    revisar_saltos(planos)
    revisar_trayectorias(planos)
    return planos, huella(planos)


def marcar_validada(nombre: str, huella_ejecutada: str) -> None:
    """Anota que la rutina corrió completa en el emulador con esa huella (así el brazo real la acepta mientras no cambie)."""
    if nombre in INCORPORADAS:
        return  # siempre cuenta como validada y no tiene archivo
    datos = _leer(nombre)
    datos["huella_validada"] = huella_ejecutada
    _ruta(nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
