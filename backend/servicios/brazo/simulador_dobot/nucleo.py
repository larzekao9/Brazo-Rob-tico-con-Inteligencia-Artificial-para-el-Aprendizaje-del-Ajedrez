"""El simulador completo: pose del TCP que se mueve en el tiempo, cola de movimientos, pinza, mundo físico, fallos y registro de comandos.

Un hilo avanza la simulación a `escala_tiempo` veces el tiempo real (o se la avanza a mano con `avanzar`, para los tests). Todo el
estado se protege con `cerrojo`; los servidores TCP y HTTP solo llaman a los métodos públicos.
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass

import chess

from backend.servicios.brazo.calibracion_brazo import CalibracionBrazo, ParametrosAgarre
from backend.servicios.brazo.simulador_dobot import cinematica
from backend.servicios.brazo.simulador_dobot.mundo import GeometriaTablero, MundoFisico, MundoGeometrico
from backend.servicios.brazo.simulador_dobot.parametros import PERFILES_PIEZAS, ParametrosSimulador
from backend.servicios.brazo.simulador_dobot.pinza_simulada import PinzaSimulada

MODO_APAGADO, MODO_DESHABILITADO, MODO_LIBRE, MODO_ARRASTRE, MODO_EJECUTANDO = 3, 4, 5, 6, 7
MODO_ALARMA, MODO_PAUSA, MODO_COLISION = 9, 10, 11
Pose = tuple[float, float, float, float, float, float]
MAXIMO_PASOS_POR_CICLO = 200
UMBRAL_CHOQUE_MM = 2.0


class ErrorDeComando(Exception):
    """Un comando que el controlador rechazaría; `codigo` es el `ErrorID` que se devuelve."""

    def __init__(self, codigo: int, motivo: str = ""):
        super().__init__(motivo)
        self.codigo, self.motivo = codigo, motivo


@dataclass
class Movimiento:
    """Un movimiento de la cola: de la pose actual a `fin`, interpolado en articulaciones (`articular`) o en línea recta."""

    identificador: int
    fin: Pose
    articular: bool
    angulos_fin: tuple[float, ...]
    velocidad_pct: float
    aceleracion_pct: float
    velocidad_mm_s: float | None
    inicio: Pose | None = None
    angulos_inicio: tuple[float, ...] | None = None
    duracion: float = 0.0
    transcurrido: float = 0.0


@dataclass
class Fallos:
    """Fallos inyectables desde el front."""

    errores_proximo_movimiento: int = 0
    pinza_no_responde: bool = False
    alarma: bool = False
    colision: bool = False
    no_tcp: bool = False
    dedos_resbaladizos: bool = False

    def como_dict(self) -> dict:
        return dict(self.__dict__)


def _minimo_jerk(tau: float) -> float:
    return tau**3 * (10 - 15 * tau + 6 * tau**2)


def _diferencia_angular(a: float, b: float) -> float:
    return (b - a + 180.0) % 360.0 - 180.0


class Simulador:
    """Brazo + pinza + mundo. Ver el docstring del módulo."""

    def __init__(
        self,
        calibracion: CalibracionBrazo,
        agarre: ParametrosAgarre,
        fen: str = chess.STARTING_FEN,
        con_fisica: bool = True,
        parametros: ParametrosSimulador | None = None,
        escala_tiempo: float = 1.0,
        tiempo_real: bool = True,
    ):
        from backend.servicios.brazo.simulador_dobot.calibracion_ejemplo import Z_TOPE_EJEMPLO

        self.parametros = parametros or ParametrosSimulador()
        self.calibracion, self.agarre = calibracion, agarre
        self.z_tope = agarre.z_tope if agarre.z_tope is not None else Z_TOPE_EJEMPLO
        self.con_fisica = con_fisica
        self.escala_tiempo, self.tiempo_real = escala_tiempo, tiempo_real
        self.cerrojo = threading.RLock()
        self.log: deque[dict] = deque(maxlen=400)
        self.fallos = Fallos()
        self.pausado = False
        self.geometria = GeometriaTablero.desde_posiciones(
            calibracion.posiciones_casillas, self.z_tope - self.parametros.fisicos.longitud_punta_mm
        )
        self.rz_referencia = calibracion.orientacion[2]
        self._hilo: threading.Thread | None = None
        self._detener_hilo = threading.Event()
        self.mundo = None
        self.velocidad_efectiva = 0.0
        self.choque = False
        self._avisos_choque = 0
        self.piezas_danadas: set[int] = set()
        self._tiempo_apretada: dict[int, int] = {}
        self.fen = fen
        self._arrancar(fen)

    # --- ciclo de vida ----------------------------------------------------------------------------------------------------
    def _pose_inicial(self) -> Pose:
        pose = cinematica.pose_para_angulos(self.calibracion.angulos_cero)
        if pose[2] < self.z_tope + 120:
            x, y = self.geometria.centro_casilla("d4")
            pose = (x, y - 150, self.z_tope + 250, *self.parametros.robot.orientacion_herramienta, self.rz_referencia)
            self.registrar("sim", "los ángulos cero de la calibración no son coherentes con el modelo esquemático: arranco en una pose sobre el tablero")
        return pose

    def _arrancar(self, fen: str) -> None:
        self.fen = fen
        self.tiempo = 0.0
        self.velocidad_global = 100
        self.habilitado, self.encendido, self.arrastrando, self.pausa_robot = True, True, False, False
        self.control_tcp = True
        self.cola: deque[Movimiento] = deque()
        self.actual: Movimiento | None = None
        self.siguiente_id = 1
        self.pose = self._pose_inicial()
        self.angulos = cinematica.angulos_para_pose(self.pose[0], self.pose[1], self.pose[2], self.pose[5]) or self.calibracion.angulos_cero
        self.pose_fin_cola = self.pose
        self.angulos_fin_cola = self.angulos
        clase = MundoFisico if self.con_fisica else MundoGeometrico
        punta = self._punta(self.pose)
        self.mundo = clase(self.geometria, self.parametros.fisicos, fen, self._yaw_dedos(self.pose), punta)
        self.pinza = PinzaSimulada(self.mundo, self.parametros.fisicos, self.registrar)
        self.pinza.ancho_mm = self.parametros.fisicos.carrera_mm
        self.avanzar_pasos(1)

    def reiniciar(self, fen: str | None = None) -> None:
        """Vuelve a la posición cero con la pinza sin inicializar y las piezas del FEN (por defecto la posición inicial)."""
        with self.cerrojo:
            chess.Board(fen or chess.STARTING_FEN)
            self.mundo.cerrar()
            self.fallos = Fallos()
            self._arrancar(fen or chess.STARTING_FEN)
            self.registrar("sim", f"escena reiniciada ({fen or 'posición inicial'})")

    def cargar_fen(self, fen: str) -> None:
        """Pone las piezas del FEN en el tablero (sin mover el brazo ni la pinza)."""
        with self.cerrojo:
            chess.Board(fen)
            self.fen = fen
            self.mundo.cargar_fen(fen)
            self.registrar("sim", f"FEN cargado: {fen}")

    def cerrar(self) -> None:
        """Detiene el hilo y libera el mundo físico."""
        self.detener_hilo()
        with self.cerrojo:
            if self.mundo is not None:
                self.mundo.cerrar()

    # --- hilo -------------------------------------------------------------------------------------------------------------
    def iniciar_hilo(self) -> None:
        """Arranca el hilo que avanza la simulación en tiempo real (por `escala_tiempo`)."""
        if self._hilo is not None:
            return
        self._detener_hilo.clear()
        self._hilo = threading.Thread(target=self._bucle, name="simulador-dobot", daemon=True)
        self._hilo.start()

    def detener_hilo(self) -> None:
        self._detener_hilo.set()
        if self._hilo is not None:
            self._hilo.join(timeout=5)
            self._hilo = None

    def _bucle(self) -> None:
        paso = self.parametros.fisicos.paso_s
        ultimo, acumulado = time.monotonic(), 0.0
        ventana_real, ventana_sim = ultimo, 0.0
        while not self._detener_hilo.is_set():
            ahora = time.monotonic()
            if not self.pausado:
                acumulado += (ahora - ultimo) * self.escala_tiempo
            ultimo = ahora
            pasos = int(acumulado / paso)
            if pasos > MAXIMO_PASOS_POR_CICLO:
                pasos, acumulado = MAXIMO_PASOS_POR_CICLO, 0.0
            else:
                acumulado -= pasos * paso
            if pasos:
                self.avanzar_pasos(pasos)
                ventana_sim += pasos * paso
            if ahora - ventana_real >= 1.0:
                self.velocidad_efectiva = 0.0 if self.pausado else ventana_sim / (ahora - ventana_real)
                ventana_real, ventana_sim = ahora, 0.0
            time.sleep(0.003)

    def avanzar(self, segundos: float) -> None:
        """Avanza la simulación `segundos` de tiempo simulado (para tests y uso sin hilo)."""
        self.avanzar_pasos(int(round(segundos / self.parametros.fisicos.paso_s)))

    def avanzar_pasos(self, pasos: int) -> None:
        paso = self.parametros.fisicos.paso_s
        with self.cerrojo:
            for _ in range(pasos):
                self.tiempo += paso
                self._avanzar_movimiento(paso)
                self.mundo.fijar_herramienta(self._punta(self.pose), self._yaw_dedos(self.pose))
                self.mundo.avanzar(1)
                self.pinza.actualizar(self.tiempo)
                self._vigilar_choque()

    def _vigilar_choque(self) -> None:
        if int(self.tiempo / self.parametros.fisicos.paso_s) % 12:
            return
        self._vigilar_danos()
        desviacion = self.mundo.desviacion_herramienta_mm()
        self._avisos_choque = self._avisos_choque + 1 if desviacion > UMBRAL_CHOQUE_MM else 0
        if self._avisos_choque >= 3 and not self.choque:
            self.choque = True
            self.registrar("sim", f"la pinza quedó {desviacion:.1f} mm atrás de la pose pedida: está chocando con una pieza o el tablero")
        elif self._avisos_choque == 0:
            self.choque = False

    def _vigilar_danos(self) -> None:
        """Una pieza que un dedo aprieta con más de `fuerza_rotura_n` durante un rato se marca como dañada (la apretó o la aplastó)."""
        limite = self.parametros.fisicos.fuerza_rotura_n
        apretadas = {pieza for (pieza, _), fuerza in self.mundo.fuerzas_por_pieza_y_dedo_n().items() if fuerza > limite}
        for pieza in list(self._tiempo_apretada):
            if pieza not in apretadas:
                del self._tiempo_apretada[pieza]
        for pieza in apretadas:
            self._tiempo_apretada[pieza] = self._tiempo_apretada.get(pieza, 0) + 1
            if self._tiempo_apretada[pieza] == 4 and pieza not in self.piezas_danadas:
                self.piezas_danadas.add(pieza)
                simbolo = next((p.simbolo for p in self.mundo.piezas() if p.identificador == pieza), "?")
                self.registrar("sim", f"la pieza {simbolo} quedó dañada: un dedo la apretó con más de {limite:.0f} N")

    # --- geometría de la herramienta --------------------------------------------------------------------------------------
    def _punta(self, pose: Pose) -> tuple[float, float, float]:
        z = max(pose[2] - self.parametros.fisicos.longitud_punta_mm, self.geometria.z_superficie)
        return pose[0], pose[1], z

    def _yaw_dedos(self, pose: Pose) -> float:
        return self.geometria.angulo_u_grados + (pose[5] - self.rz_referencia)

    # --- estado -----------------------------------------------------------------------------------------------------------
    def modo(self) -> int:
        """`RobotMode()` del controlador real."""
        if self.fallos.alarma:
            return MODO_ALARMA
        if self.fallos.colision:
            return MODO_COLISION
        if not self.encendido:
            return MODO_APAGADO
        if not self.habilitado:
            return MODO_DESHABILITADO
        if self.pausa_robot:
            return MODO_PAUSA
        if self.arrastrando:
            return MODO_ARRASTRE
        return MODO_EJECUTANDO if (self.actual is not None or self.cola) else MODO_LIBRE

    def registrar(self, origen: str, texto: str) -> None:
        with self.cerrojo:
            self.log.append({"t": round(self.tiempo, 3), "origen": origen, "texto": texto})

    # --- movimiento -------------------------------------------------------------------------------------------------------
    def _validar_para_mover(self) -> None:
        if self.fallos.alarma or self.fallos.colision:
            raise ErrorDeComando(-2, "robot en alarma")
        if not self.encendido:
            raise ErrorDeComando(-4, "robot apagado")
        if not self.habilitado:
            raise ErrorDeComando(-1, "robot deshabilitado")
        if self.fallos.errores_proximo_movimiento > 0:
            self.fallos.errores_proximo_movimiento -= 1
            raise ErrorDeComando(-1, "fallo inyectado")

    def encolar_pose(self, pose: Pose, articular: bool, velocidad_pct: float, aceleracion_pct: float, velocidad_mm_s: float | None) -> int:
        """`MovJ`/`MovL` a una pose. Rechaza (`ErrorDeComando`) si está fuera de alcance o más baja que el tablero."""
        with self.cerrojo:
            self._validar_para_mover()
            minimo = self.z_tope - self.parametros.fisicos.margen_agarre_tablero_mm
            if pose[2] < minimo:
                raise ErrorDeComando(-1, f"z={pose[2]:.2f} baja más que el tablero (z_tope={self.z_tope:.2f})")
            angulos = cinematica.angulos_para_pose(pose[0], pose[1], pose[2], pose[5])
            if angulos is None:
                raise ErrorDeComando(-1, f"la pose {tuple(round(v, 1) for v in pose[:3])} está fuera de alcance")
            if abs(abs(pose[3]) - 180.0) > 10.0 or abs(pose[4]) > 10.0:
                self.registrar("sim", "inclinación de la herramienta ignorada: el modelo la mantiene vertical")
            return self._encolar(Movimiento(self.siguiente_id, pose, articular, angulos, velocidad_pct, aceleracion_pct, velocidad_mm_s))

    def encolar_angulos(self, angulos: tuple[float, ...], velocidad_pct: float, aceleracion_pct: float) -> int:
        """`MovJ(joint=...)`: la pose sale de la cinemática esquemática."""
        with self.cerrojo:
            self._validar_para_mover()
            return self._encolar(Movimiento(self.siguiente_id, cinematica.pose_para_angulos(angulos), True, angulos, velocidad_pct, aceleracion_pct, None))

    def _encolar(self, movimiento: Movimiento) -> int:
        self.siguiente_id += 1
        self.cola.append(movimiento)
        self.pose_fin_cola, self.angulos_fin_cola = movimiento.fin, movimiento.angulos_fin
        return movimiento.identificador

    def pose_para_relativo(self, dx: float, dy: float, dz: float) -> Pose:
        x, y, z, rx, ry, rz = self.pose_fin_cola
        return (x + dx, y + dy, z + dz, rx, ry, rz)

    def detener(self) -> None:
        """`Stop()`: vacía la cola y frena donde está."""
        with self.cerrojo:
            self.cola.clear()
            self.actual = None
            self.pose_fin_cola, self.angulos_fin_cola = self.pose, self.angulos

    def _iniciar(self, movimiento: Movimiento) -> None:
        movimiento.inicio, movimiento.angulos_inicio = self.pose, self.angulos
        factor = max(1, self.velocidad_global) / 100
        robot = self.parametros.robot
        if movimiento.articular:
            delta = max(abs(_diferencia_angular(a, b)) for a, b in zip(movimiento.angulos_inicio, movimiento.angulos_fin))
            velocidad = robot.velocidad_articular_max_grados_s * movimiento.velocidad_pct / 100 * factor
            duracion = delta / velocidad
        else:
            distancia = math.dist(movimiento.inicio[:3], movimiento.fin[:3])
            giro = abs(_diferencia_angular(movimiento.inicio[5], movimiento.fin[5]))
            velocidad = movimiento.velocidad_mm_s or robot.velocidad_lineal_max_mm_s * movimiento.velocidad_pct / 100 * factor
            duracion = max(distancia / velocidad, giro / (robot.velocidad_articular_max_grados_s * movimiento.velocidad_pct / 100 * factor))
        recorrido = math.dist(movimiento.inicio[:3], movimiento.fin[:3])
        por_aceleracion = math.sqrt(5.7735 * recorrido / (robot.aceleracion_max_mm_s2 * max(1.0, movimiento.aceleracion_pct) / 100))
        movimiento.duracion = max(duracion * 1.2, por_aceleracion, robot.duracion_minima_s)
        self.actual = movimiento

    def _avanzar_movimiento(self, paso: float) -> None:
        if self.fallos.alarma or self.fallos.colision or self.pausa_robot or not self.habilitado:
            return
        if self.actual is None and self.cola:
            self._iniciar(self.cola.popleft())
        movimiento = self.actual
        if movimiento is None:
            return
        movimiento.transcurrido += paso
        tau = min(1.0, movimiento.transcurrido / movimiento.duracion)
        s = _minimo_jerk(tau)
        if movimiento.articular:
            angulos = tuple(a + _diferencia_angular(a, b) * s for a, b in zip(movimiento.angulos_inicio, movimiento.angulos_fin))
            self.angulos, self.pose = angulos, cinematica.pose_para_angulos(angulos)
        else:
            i, f = movimiento.inicio, movimiento.fin
            x, y, z = (a + (b - a) * s for a, b in zip(i[:3], f[:3]))
            rz = i[5] + _diferencia_angular(i[5], f[5]) * s
            self.pose = (x, y, z, f[3], f[4], rz)
            self.angulos = cinematica.angulos_para_pose(x, y, z, rz) or self.angulos
        if tau >= 1.0:
            self.pose = movimiento.fin if not movimiento.articular else cinematica.pose_para_angulos(movimiento.angulos_fin)
            self.angulos = movimiento.angulos_fin
            self.actual = None

    # --- fallos -----------------------------------------------------------------------------------------------------------
    def inyectar_fallo(self, tipo: str, valor=True) -> None:
        """Activa, desactiva o dispara un fallo; `tipo` es uno de los nombres de `Fallos` o `pieza_cae`."""
        with self.cerrojo:
            if tipo == "pieza_cae":
                self.mundo.aflojar_dedos(0.8)
                self.registrar("fallo", "los dedos aflojan: si hay una pieza apretada, se cae")
            elif tipo == "error_proximo_movimiento":
                self.fallos.errores_proximo_movimiento = int(valor) if valor else 0
            elif tipo == "dedos_resbaladizos":
                self.fallos.dedos_resbaladizos = bool(valor)
                self.mundo.fijar_friccion_dedos(self.parametros.fisicos.friccion_dedos_fallo if valor else self.parametros.fisicos.friccion_dedos)
            elif tipo in ("pinza_no_responde", "alarma", "colision", "no_tcp"):
                setattr(self.fallos, tipo, bool(valor))
            else:
                raise ValueError(f"fallo desconocido: {tipo}")
            self.registrar("fallo", f"{tipo} = {valor}")

    def limpiar_errores(self) -> None:
        """`ClearError()`."""
        with self.cerrojo:
            self.fallos.alarma = self.fallos.colision = False

    # --- instantánea para el front ------------------------------------------------------------------------------------------
    def instantanea(self) -> dict:
        """Todo lo que el front necesita para dibujarse, en un diccionario serializable a JSON."""
        with self.cerrojo:
            g, f = self.geometria, self.parametros.fisicos
            piezas = []
            for pieza in self.mundo.piezas():
                perfil = PERFILES_PIEZAS[pieza.tipo]
                casilla = g.casilla_en(pieza.x, pieza.y)
                sobre_tablero = casilla is not None and pieza.z > g.z_superficie - 3
                piezas.append(
                    {
                        "id": pieza.identificador, "simbolo": pieza.simbolo, "nombre": perfil.nombre,
                        "x": round(pieza.x, 2), "y": round(pieza.y, 2), "z": round(pieza.z, 2),
                        "inclinacion": round(pieza.inclinacion_grados, 1), "casilla": casilla if sobre_tablero else None,
                        "origen": pieza.casilla_inicial, "yaw": round(pieza.yaw_grados, 1), "alto": perfil.alto_mm, "ancho": perfil.ancho_base_mm,
                        "volcada": pieza.inclinacion_grados > f.inclinacion_pieza_caida_grados,
                        "danada": pieza.identificador in self.piezas_danadas or (g.z_superficie - 10 < pieza.z < g.z_superficie - f.aplastamiento_mm),
                    }
                )
            movimiento = self.actual
            return {
                "tiempo": round(self.tiempo, 2), "pausado": self.pausado, "escala_tiempo": self.escala_tiempo,
                "velocidad_efectiva": round(self.velocidad_efectiva, 2), "con_fisica": self.con_fisica,
                "modo": self.modo(), "choque": self.choque, "velocidad_global": self.velocidad_global, "cola": len(self.cola) + (1 if movimiento else 0),
                "pose": [round(v, 3) for v in self.pose], "angulos": [round(v, 3) for v in self.angulos],
                "brazo": [[round(c, 1) for c in p] for p in cinematica.puntos_del_brazo(self.angulos)],
                "pinza": {
                    "inicializada": self.pinza.inicializada, "ancho_mm": round(self.pinza.ancho_mm, 2), "posicion": self.pinza.posicion_actual,
                    "objetivo": self.pinza.posicion_objetivo, "fuerza_pct": self.pinza.fuerza_pct, "velocidad_pct": self.pinza.velocidad_pct,
                    "agarre": self.pinza._agarre_visible, "agarre_real": self.pinza.agarre,
                    "fuerza_contacto_n": round(self.pinza.fuerza_contacto_n, 2),
                },
                "herramienta": {"punta": [round(v, 2) for v in self._punta(self.pose)], "yaw": round(self._yaw_dedos(self.pose), 2), "largo": f.dedo_largo_mm,
                                "grosor": f.dedo_grosor_mm, "ancho": f.dedo_ancho_mm},
                "tablero": {
                    "origen_a1": g.origen_a1, "paso_u": g.paso_u, "paso_v": g.paso_v, "z": round(g.z_superficie, 2), "z_tope": self.z_tope,
                    "angulo_u": round(g.angulo_u_grados, 2),
                },
                "piezas": piezas,
                "perfiles": {k: [[s.z_inferior, s.z_superior, s.ancho_x, s.ancho_y] for s in v.segmentos] for k, v in PERFILES_PIEZAS.items()},
                "fallos": self.fallos.como_dict(), "fen": self.fen, "log": list(self.log)[-150:],
            }
