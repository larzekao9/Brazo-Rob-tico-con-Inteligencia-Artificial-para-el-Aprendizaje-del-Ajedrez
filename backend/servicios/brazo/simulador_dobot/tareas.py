"""Las operaciones de los scripts de prueba (jugada, agarre de la pinza, ajuste de apertura) hechas desde el front del simulador.

No duplican la lógica: arman un `EjecutorReal` / `PinzaDH` con un `ClienteDobot` que se conecta como cliente al propio servidor TCP del
simulador, igual que los scripts con el brazo real. Una sola tarea larga a la vez; las operaciones cortas (pinza, jog) se hacen en el
momento y se rechazan si hay una tarea moviendo el brazo.
"""
from __future__ import annotations

import dataclasses
import threading
import time

import chess

from backend.servicios.brazo.cliente_dobot import ClienteDobot, ErrorDobot
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal
from backend.servicios.brazo.pinza_dh import (
    REG_FUERZA,
    REG_POSICION,
    REG_VELOCIDAD,
    PinzaDH,
    ancho_mm_para_posicion,
)
from backend.servicios.brazo.simulador_dobot.nucleo import Simulador
from backend.servicios.brazo.simulador_dobot.parametros import PERFILES_PIEZAS

MODOS_JUGADA = ("completa", "solo_bajar", "solo_cerrar")
TIPOS_PIEZA = "pnbrqk"
VELOCIDAD_POR_DEFECTO = 20
DURACION_MUESTREO_S = 5.0
INTERVALO_MUESTREO_S = 0.1
LIMITE_JOG_MM = 300.0
VELOCIDAD_JOG_MM_S = 100
LUZ_MINIMA_MM = 0.5
LUZ_DE_SOBRA_MM = 3.0
CASILLA_APERTURA_POR_DEFECTO = "c5"
APERTURA_INICIAL_POR_DEFECTO = 700
HOLGURA_POR_DEFECTO = 40


class ErrorApi(Exception):
    """Un error que el servidor HTTP devuelve tal cual: `codigo` HTTP y `mensaje` para el front."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo, self.mensaje = codigo, mensaje


class TareaCancelada(Exception):
    """Se pidió cancelar: corta la tarea en el siguiente comando que intente mandar al simulador."""


class _ClienteCancelable(ClienteDobot):
    """`ClienteDobot` que deja de mandar comandos cuando se cancela la tarea."""

    def __init__(self, *argumentos, cancelacion: threading.Event, **opciones):
        super().__init__(*argumentos, **opciones)
        self.cancelacion = cancelacion

    def enviar(self, comando: str):
        if self.cancelacion.is_set():
            raise TareaCancelada()
        return super().enviar(comando)


def evaluar_apertura(pieza: str, ancho_mm: float) -> dict:
    """Si una pieza de tipo `pieza` pasa entre dedos abiertos `ancho_mm`, con las mismas medidas que usa la física (parte más ancha)."""
    ancho_pieza = PERFILES_PIEZAS[pieza].ancho_maximo_mm
    luz = ancho_mm - ancho_pieza
    if luz < 0:
        veredicto = "no_pasa"
    elif luz < LUZ_MINIMA_MM:
        veredicto = "roza"
    elif luz > LUZ_DE_SOBRA_MM:
        veredicto = "sobra"
    else:
        veredicto = "pasa"
    return {
        "ancho_pieza_mm": round(ancho_pieza, 2), "luz_mm": round(luz, 2), "veredicto": veredicto,
        "pasa": luz >= LUZ_MINIMA_MM, "roza": luz < LUZ_MINIMA_MM,
    }


def _redondeada(pose) -> list[float]:
    return [round(float(v), 2) for v in pose]


class GestorTareas:
    """Estado y ejecución de las operaciones del front sobre un `Simulador` que escucha en `puerto_dashboard`."""

    def __init__(self, simulador: Simulador, puerto_dashboard: int | None, host: str = "127.0.0.1"):
        self.simulador, self.puerto, self.host = simulador, puerto_dashboard, host
        self._cerrojo = threading.RLock()
        self._cerrojo_ejecutor = threading.RLock()
        self._cancelacion = threading.Event()
        self._continuar = threading.Event()
        self._hilo: threading.Thread | None = None
        self._ejecutor: EjecutorReal | None = None
        self._tarea = self._tarea_libre()
        self._apertura: dict | None = None

    @staticmethod
    def _tarea_libre() -> dict:
        return {"nombre": "", "estado": "libre", "mensaje": "", "error": None}

    # --- estado -----------------------------------------------------------------------------------------------------------
    def resumen(self) -> dict:
        """Lo que se agrega a `/api/estado`: la tarea actual y la sesión de ajuste de apertura (o `None`)."""
        with self._cerrojo:
            return {"tarea": dict(self._tarea), "apertura": dict(self._apertura) if self._apertura else None}

    def _actualizar(self, **campos) -> None:
        with self._cerrojo:
            self._tarea.update(campos)

    def _exigir_dashboard(self) -> int:
        if self.puerto is None:
            raise ErrorApi(503, "el servidor HTTP no conoce el puerto del dashboard TCP: arrancá el simulador con scripts/simulador_brazo.py")
        return self.puerto

    def _corriendo(self) -> bool:
        return self._tarea["estado"] == "corriendo"

    def _exigir_sin_tarea(self, permitir_esperando: bool = False) -> None:
        with self._cerrojo:
            if self._corriendo() and not (permitir_esperando and self._tarea.get("esperando")):
                raise ErrorApi(409, f"hay una tarea en curso ({self._tarea['nombre']}): esperá a que termine o cancelala")

    def _nuevo_cliente(self, velocidad: int | None = None) -> ClienteDobot:
        velocidad = velocidad if velocidad is not None else self.simulador.velocidad_global
        return _ClienteCancelable(self.host, self._exigir_dashboard(), 5.0, velocidad, cancelacion=self._cancelacion)

    def _crear_ejecutor(self, parametros, velocidad: int) -> EjecutorReal:
        calibracion = self.simulador.calibracion
        try:
            return EjecutorReal(
                host=self.host, puerto_dashboard=self._exigir_dashboard(), posiciones_casillas=calibracion.posiciones_casillas,
                orientacion=calibracion.orientacion, angulos_cero=calibracion.angulos_cero, velocidad_global=velocidad, parametros=parametros,
                cliente=self._nuevo_cliente(velocidad),
            )
        except ValueError as error:
            raise ErrorApi(400, str(error)) from error

    # --- ciclo de la tarea ------------------------------------------------------------------------------------------------
    def _lanzar(self, nombre: str, trabajo, ejecutor: EjecutorReal | None, **extra) -> None:
        with self._cerrojo:
            self._exigir_sin_tarea()
            self._cancelacion.clear()
            self._continuar.clear()
            self._ejecutor = ejecutor
            self._tarea = {"nombre": nombre, "estado": "corriendo", "mensaje": "iniciando", "error": None, "esperando": False, "detalle": {}, **extra}
            self._hilo = threading.Thread(target=self._correr, args=(trabajo,), name="tarea-simulador", daemon=True)
            self._hilo.start()

    def _correr(self, trabajo) -> None:
        cancelada = False
        try:
            mensaje = trabajo()
            self._actualizar(estado="ok", mensaje=mensaje or "listo", esperando=False)
        except TareaCancelada:
            cancelada = True
            self._actualizar(estado="error", mensaje="cancelada", error="Tarea cancelada", cancelada=True, esperando=False)
        except Exception as error:  # el front muestra cualquier fallo del ejecutor (pieza no agarrada, alarma, timeout...)
            self._actualizar(estado="error", mensaje="falló", error=f"{type(error).__name__}: {error}", esperando=False)
        finally:
            ejecutor, self._ejecutor = self._ejecutor, None
            with self._cerrojo:
                self._apertura = None
            if ejecutor is not None:
                try:
                    if cancelada:
                        ejecutor.cliente.cerrar()
                    else:
                        ejecutor.desconectar()
                except Exception:
                    ejecutor.cliente.cerrar()

    def _esperar_continuar(self, mensaje: str) -> None:
        self._actualizar(mensaje=mensaje, esperando=True)
        while not self._continuar.wait(0.05):
            if self._cancelacion.is_set():
                raise TareaCancelada()
        self._actualizar(esperando=False)

    def continuar(self) -> dict:
        """Libera una tarea que está esperando (`solo_bajar`, `solo_cerrar`): sube y vuelve a cero."""
        with self._cerrojo:
            if not (self._corriendo() and self._tarea.get("esperando")):
                raise ErrorApi(409, "no hay ninguna tarea esperando para continuar")
            self._continuar.set()
        return self.resumen()

    def cancelar(self) -> dict:
        """Aborta la tarea: frena el brazo donde está. Si estaba esperando con el brazo abajo, hace el retiro normal (sube y vuelve a cero)."""
        with self._cerrojo:
            if not self._corriendo():
                raise ErrorApi(409, "no hay ninguna tarea en curso")
            if self._tarea.get("esperando"):
                self._tarea["cancelada"] = True
                self._continuar.set()
            else:
                self._cancelacion.set()
                self.simulador.detener()
        return self.resumen()

    def cancelar_todo(self, esperar: bool = True) -> None:
        """Corta cualquier tarea y espera a que su hilo termine (para reiniciar la escena sin que la pise)."""
        with self._cerrojo:
            hilo = self._hilo
            if not self._corriendo():
                return
            self._cancelacion.set()
        self.simulador.detener()
        if esperar and hilo is not None:
            hilo.join(timeout=5)

    # --- jugada -----------------------------------------------------------------------------------------------------------
    def _preparar_jugada(self, uci: str) -> tuple[chess.Board, chess.Move, str]:
        try:
            jugada = chess.Move.from_uci(str(uci))
        except ValueError as error:
            raise ErrorApi(400, f"jugada UCI inválida: {uci!r}") from error
        piezas = self.simulador.tablero_piezas()
        origen = chess.square_name(jugada.from_square)
        if origen not in piezas:
            raise ErrorApi(400, f"no hay ninguna pieza apoyada en {origen}")
        tablero = chess.Board(None)
        for casilla, simbolo in piezas.items():
            tablero.set_piece_at(chess.parse_square(casilla), chess.Piece.from_symbol(simbolo))
        tablero.turn = tablero.color_at(jugada.from_square)
        if jugada not in tablero.legal_moves:
            raise ErrorApi(400, f"{uci} no es una jugada legal desde la posición que hay en el tablero")
        if tablero.is_capture(jugada):
            raise ErrorApi(400, f"{uci} es una captura: retirar la pieza capturada todavía no está implementado")
        return tablero, jugada, tablero.piece_at(jugada.from_square).symbol().lower()

    def _parametros_con(self, fuerza, margen_agarre):
        parametros = self.simulador.agarre
        if fuerza is not None:
            parametros = dataclasses.replace(parametros, fuerza=_entero(fuerza, "fuerza"))
        if margen_agarre is not None:
            parametros = dataclasses.replace(parametros, margen_agarre_mm=_decimal(margen_agarre, "margen_agarre"))
        return dataclasses.replace(parametros, z_tope=self.simulador.z_tope, aperturas_por_pieza=dict(parametros.aperturas_por_pieza))

    def ensayo(self, uci: str) -> dict:
        """Las poses por las que pasaría la jugada, sin mover nada (`--ensayo` de `probar_jugada_brazo.py`)."""
        tablero, jugada, pieza = self._preparar_jugada(uci)
        parametros = self._parametros_con(None, None)
        try:
            apertura = parametros.apertura_para(pieza)
            z_agarre = parametros.z_agarre
        except RuntimeError as error:
            raise ErrorApi(400, str(error)) from error
        ejecutor = self._crear_ejecutor(parametros, VELOCIDAD_POR_DEFECTO)
        poses = {}
        for nombre, cuadro in (("origen", jugada.from_square), ("destino", jugada.to_square)):
            casilla = chess.square_name(cuadro)
            poses[nombre] = {
                "casilla": casilla, "agarre": _redondeada(ejecutor._pose(casilla)),
                "segura": _redondeada(ejecutor._pose(casilla, parametros.altura_segura_mm)),
            }
        return {
            "uci": jugada.uci(), "pieza": pieza, "apertura": apertura, "ancho_mm": round(ancho_mm_para_posicion(apertura), 2),
            "z_agarre": round(z_agarre, 2), "altura_segura_mm": parametros.altura_segura_mm, "giro_diagonal_grados": parametros.giro_diagonal_grados,
            "margen_agarre_mm": parametros.margen_agarre_mm, "fuerza": parametros.fuerza, "origen": poses["origen"], "destino": poses["destino"],
        }

    def iniciar_jugada(self, uci: str, modo: str = "completa", fuerza=None, margen_agarre=None, velocidad=None) -> dict:
        """Lanza la jugada en un hilo (`probar_jugada_brazo.py`); el resultado queda en `resumen()["tarea"]`."""
        if modo not in MODOS_JUGADA:
            raise ErrorApi(400, f"modo desconocido: {modo!r} (completa, solo_bajar o solo_cerrar)")
        self._exigir_dashboard()
        self._exigir_sin_tarea()
        tablero, jugada, pieza = self._preparar_jugada(uci)
        parametros = self._parametros_con(fuerza, margen_agarre)
        try:
            parametros.apertura_para(pieza)
            parametros.z_agarre
        except RuntimeError as error:
            raise ErrorApi(400, str(error)) from error
        velocidad = VELOCIDAD_POR_DEFECTO if velocidad is None else _entero(velocidad, "velocidad")
        if not 1 <= velocidad <= 100:
            raise ErrorApi(400, "la velocidad tiene que estar entre 1 y 100")
        ejecutor = self._crear_ejecutor(parametros, velocidad)
        origen = chess.square_name(jugada.from_square)

        def trabajo() -> str:
            ejecutor.conectar()
            if modo == "completa":
                self._actualizar(mensaje=f"moviendo {jugada.uci()}")
                ejecutor.ejecutar_movimiento(tablero, jugada)
                return f"{jugada.uci()} ejecutada"
            ejecutor.cliente.mover_a_angulos(ejecutor.angulos_cero)
            ejecutor.bajar_a(origen, pieza)
            self._tarea["detalle"]["pose_abajo"] = _redondeada(ejecutor.cliente.pose())
            if modo == "solo_cerrar":
                self._muestrear_cierre(ejecutor)
            self._esperar_continuar("abajo sobre " + origen + ": esperando /api/continuar para subir")
            ejecutor.subir_de(origen, pieza)
            ejecutor.cliente.mover_a_angulos(ejecutor.angulos_cero)
            return "retirado"

        self._lanzar(f"jugada {jugada.uci()} ({modo})", trabajo, ejecutor, uci=jugada.uci(), modo=modo)
        return self.resumen()

    def _muestrear_cierre(self, ejecutor: EjecutorReal) -> None:
        """Cierra la pinza y anota agarre y posición cada 0,1 s de tiempo simulado, como `--solo-cerrar`."""
        sim = self.simulador
        muestras: list[dict] = []
        self._tarea["detalle"]["muestras"] = muestras
        self._actualizar(mensaje="cerrando la pinza")
        ejecutor.pinza.escribir(REG_POSICION, 0)
        inicio_sim, inicio_real, proxima = sim.tiempo, time.monotonic(), 0.0
        while sim.tiempo - inicio_sim < DURACION_MUESTREO_S and time.monotonic() - inicio_real < 120:
            if self._cancelacion.is_set():
                raise TareaCancelada()
            transcurrido = sim.tiempo - inicio_sim
            if transcurrido >= proxima:
                estado = ejecutor.pinza.estado()
                muestras.append({"t": round(transcurrido, 2), "agarre": estado.agarre, "posicion": estado.posicion})
                proxima += INTERVALO_MUESTREO_S
            else:
                time.sleep(0.01)

    # --- pinza sola -------------------------------------------------------------------------------------------------------
    def pinza(self, accion: str, valor=None, fuerza=None) -> dict:
        """`abrir`, `cerrar` o `mover` a `valor` (0 a 1000), y espera a que termine. Inicializa la pinza si hace falta."""
        if accion not in ("abrir", "cerrar", "mover"):
            raise ErrorApi(400, f"acción desconocida: {accion!r} (abrir, cerrar o mover)")
        if accion == "mover":
            valor = _entero(valor, "valor")
            if not 0 <= valor <= 1000:
                raise ErrorApi(400, "valor tiene que estar entre 0 y 1000")
        self._exigir_sin_tarea(permitir_esperando=True)
        sim = self.simulador
        fuerza = sim.agarre.fuerza if fuerza is None else _entero(fuerza, "fuerza")
        cliente = ClienteDobot(self.host, self._exigir_dashboard(), 5.0, sim.velocidad_global)
        try:
            pinza = PinzaDH(cliente, fuerza=fuerza, velocidad=sim.agarre.velocidad_pinza)
        except ValueError as error:
            raise ErrorApi(400, str(error)) from error
        try:
            cliente.conectar()
            pinza.conectar()
            if not pinza.estado().inicializada:
                pinza.inicializar(limite_segundos=60)
            pinza.escribir(REG_FUERZA, fuerza)
            pinza.escribir(REG_VELOCIDAD, sim.agarre.velocidad_pinza)
            objetivo = {"abrir": 1000, "cerrar": 0, "mover": valor}[accion]
            estado = pinza.mover_a(objetivo, limite_segundos=60)
        except (ErrorDobot, OSError, RuntimeError, TimeoutError) as error:
            raise ErrorApi(502, f"la pinza no respondió: {error}") from error
        finally:
            try:
                pinza.desconectar()
            except (ErrorDobot, OSError, RuntimeError):
                pass
            cliente.cerrar()
        return {"ok": True, "pinza": {"agarre": estado.agarre, "posicion": estado.posicion, "inicializada": estado.inicializada, "fuerza": fuerza}}

    def pieza_en_pinza(self, tipo) -> dict:
        """Pone a mano una pieza entre los dedos (o la retira con `None`), como hace el usuario en `probar_agarre_pinza.py`."""
        self._exigir_sin_tarea(permitir_esperando=True)
        try:
            self.simulador.pieza_en_pinza(tipo)
        except ValueError as error:
            raise ErrorApi(409 if "abrila" in str(error) else 400, str(error)) from error
        return {"ok": True, "tipo": tipo}

    # --- jog --------------------------------------------------------------------------------------------------------------
    def jog(self, dx, dy, dz) -> dict:
        """Mueve el TCP en línea recta `dx, dy, dz` mm respecto de donde está, para buscar a mano la altura del tablero."""
        deltas = [_decimal(v, n) for v, n in ((dx, "dx"), (dy, "dy"), (dz, "dz"))]
        if any(abs(v) > LIMITE_JOG_MM for v in deltas):
            raise ErrorApi(400, f"cada desplazamiento tiene que ser de {LIMITE_JOG_MM:g} mm o menos")
        self._exigir_sin_tarea()
        cliente = ClienteDobot(self.host, self._exigir_dashboard(), 5.0, self.simulador.velocidad_global)
        try:
            cliente.conectar()
            cliente.mover_relativo(*deltas, velocidad_mm_s=VELOCIDAD_JOG_MM_S)
            pose = cliente.pose()
        except (ErrorDobot, OSError, TimeoutError) as error:
            motivo = next((e["texto"] for e in reversed(list(self.simulador.log)) if "rechazado" in e["texto"]), str(error))
            raise ErrorApi(400, f"el simulador no hizo el movimiento: {motivo}") from error
        finally:
            cliente.cerrar()
        return {"ok": True, "pose": _redondeada(pose)}

    # --- ajuste de apertura (ajustar_apertura_pieza.py) -------------------------------------------------------------------------
    def apertura_iniciar(self, pieza, inicial=None, casilla=None, velocidad=None) -> dict:
        """Baja con la pinza abierta a una casilla vacía y queda lista para `apertura_mover`."""
        pieza = str(pieza or "").lower()
        if pieza not in TIPOS_PIEZA or len(pieza) != 1:
            raise ErrorApi(400, "pieza tiene que ser p, n, b, r, q o k")
        inicial = APERTURA_INICIAL_POR_DEFECTO if inicial is None else _entero(inicial, "inicial")
        if not 0 <= inicial <= 1000:
            raise ErrorApi(400, "inicial tiene que estar entre 0 y 1000")
        casilla = str(casilla or CASILLA_APERTURA_POR_DEFECTO).lower()
        try:
            chess.parse_square(casilla)
        except ValueError as error:
            raise ErrorApi(400, f"casilla inválida: {casilla!r}") from error
        self._exigir_dashboard()
        self._exigir_sin_tarea()
        ocupadas = self.simulador.tablero_piezas()
        if casilla in ocupadas:
            raise ErrorApi(400, f"{casilla} tiene una pieza: la casilla tiene que estar vacía")
        cuadro = chess.parse_square(casilla)
        cercanas = sorted(c for c in ocupadas if chess.square_distance(cuadro, chess.parse_square(c)) <= 1)
        parametros = self._parametros_con(None, None)
        parametros = dataclasses.replace(parametros, aperturas_por_pieza={**parametros.aperturas_por_pieza, pieza: inicial})
        velocidad = VELOCIDAD_POR_DEFECTO if velocidad is None else _entero(velocidad, "velocidad")
        ejecutor = self._crear_ejecutor(parametros, velocidad)
        with self._cerrojo:
            self._apertura = {
                "pieza": pieza, "casilla": casilla, "apertura": inicial, "mm": round(ancho_mm_para_posicion(inicial), 2), "lista": False,
                "terminando": False, "guardada": None, "avisos": [f"hay piezas pegadas a {casilla}: {', '.join(cercanas)}"] if cercanas else [],
                **evaluar_apertura(pieza, ancho_mm_para_posicion(inicial)),
            }

        def trabajo() -> str:
            ejecutor.conectar()
            ejecutor.cliente.mover_a_angulos(ejecutor.angulos_cero)
            ejecutor.bajar_a(casilla, pieza)
            with self._cerrojo:
                self._apertura["lista"] = True
            self._esperar_continuar(f"abajo en {casilla} con apertura {self._apertura['apertura']}: metele el {PERFILES_PIEZAS[pieza].nombre} (ajustá con /api/apertura/mover)")
            with self._cerrojo:
                self._apertura["terminando"] = True
            with self._cerrojo_ejecutor:
                apertura = self._apertura["apertura"]
                ejecutor.parametros.aperturas_por_pieza[pieza] = apertura
                ejecutor.pinza.mover_a(apertura)
            ejecutor.subir_de(casilla, pieza)
            ejecutor.cliente.mover_a_angulos(ejecutor.angulos_cero)
            return "terminado"

        try:
            self._lanzar(f"apertura de la pieza {pieza}", trabajo, ejecutor, pieza=pieza, casilla=casilla)
        except ErrorApi:
            with self._cerrojo:
                self._apertura = None
            raise
        return self.resumen()

    def _sesion_lista(self) -> dict:
        with self._cerrojo:
            if self._apertura is None or not self._corriendo():
                raise ErrorApi(409, "no hay un ajuste de apertura en curso: iniciá uno con /api/apertura/iniciar")
            if not self._apertura["lista"] or self._apertura["terminando"]:
                raise ErrorApi(409, "el brazo todavía está bajando o ya está terminando")
            return self._apertura

    def apertura_mover(self, valor=None, delta=None) -> dict:
        """Lleva la pinza a `valor` (0 a 1000) o la mueve `delta` desde la apertura actual, y dice si la pieza pasa."""
        if (valor is None) == (delta is None):
            raise ErrorApi(400, "mandá 'valor' o 'delta' (uno solo)")
        sesion = self._sesion_lista()
        nueva = _entero(valor, "valor") if valor is not None else sesion["apertura"] + _entero(delta, "delta")
        if not 0 <= nueva <= 1000:
            raise ErrorApi(400, f"fuera de rango (0 a 1000): {nueva}")
        with self._cerrojo_ejecutor:
            self._sesion_lista()
            try:
                self._ejecutor.pinza.mover_a(nueva, limite_segundos=60)
            except TareaCancelada as error:
                raise ErrorApi(409, "la tarea fue cancelada") from error
            except (ErrorDobot, OSError, RuntimeError, TimeoutError) as error:
                raise ErrorApi(502, f"la pinza no respondió: {error}") from error
        ancho_real = self.simulador.pinza.ancho_mm
        with self._cerrojo:
            sesion.update(apertura=nueva, mm=round(ancho_mm_para_posicion(nueva), 2), **evaluar_apertura(sesion["pieza"], ancho_real))
            return dict(sesion)

    def apertura_guardar(self, holgura=None) -> dict:
        """Guarda la apertura actual más `holgura` como la de esa pieza en la calibración DEL SIMULADOR."""
        holgura = HOLGURA_POR_DEFECTO if holgura is None else _entero(holgura, "holgura")
        if holgura < 0:
            raise ErrorApi(400, "holgura no puede ser negativa")
        sesion = self._sesion_lista()
        final = min(1000, sesion["apertura"] + holgura)
        try:
            self.simulador.actualizar_parametros({"aperturas_por_pieza": {sesion["pieza"]: final}})
        except ValueError as error:
            raise ErrorApi(400, str(error)) from error
        with self._cerrojo:
            sesion["guardada"] = final
            return {"ok": True, "pieza": sesion["pieza"], "guardada": final, "mm": round(ancho_mm_para_posicion(final), 2), "apertura": dict(sesion)}

    def apertura_terminar(self) -> dict:
        """Sube y vuelve a la posición cero (con la apertura que quedó), terminando el ajuste."""
        self._sesion_lista()
        self._continuar.set()
        return self.resumen()


def _entero(valor, nombre: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or int(valor) != valor:
        raise ErrorApi(400, f"{nombre} tiene que ser un número entero")
    return int(valor)


def _decimal(valor, nombre: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorApi(400, f"{nombre} tiene que ser un número")
    return float(valor)
