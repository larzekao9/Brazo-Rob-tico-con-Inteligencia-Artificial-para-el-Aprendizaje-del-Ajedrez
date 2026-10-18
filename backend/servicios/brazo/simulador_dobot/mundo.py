"""El mundo físico del simulador: tablero, piezas Staunton y pinza con dedos prismáticos, simulados con PyBullet (conexión DIRECT).

Se trabaja en CGS (1 unidad = 1 cm, masas en gramos, fuerzas en dinas) porque PyBullet se comporta mal con objetos de pocos milímetros
en metros. Toda llamada a PyBullet lleva `physicsClientId`, así que pueden convivir varios mundos. El brazo no se simula: la base de
la pinza sigue, mediante una restricción rígida, la pose que le dicta `fijar_herramienta`. Los dedos, las piezas y el tablero sí son
cuerpos con contacto y fricción.

`MundoGeometrico` es la alternativa sin PyBullet (`--sin-fisica`): las piezas se mueven con los dedos si están entre ellos, pero no hay
choques, vuelcos ni fricción.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import chess

from backend.servicios.brazo.simulador_dobot.parametros import PERFILES_PIEZAS, ParametrosFisicos, PerfilPieza

MM = 0.1
"""Un milímetro, en unidades del mundo (cm)."""
NEWTON = 1.0e5
"""Un newton, en dinas (g·cm/s²)."""
GANANCIA_DEDOS = 30.0
"""1/s: cuánto se frena la velocidad de los dedos al acercarse al ancho pedido."""
TOLERANCIA_DEDOS = 0.02
"""cm (0,2 mm) por semieje: error de posición que se da por llegado."""
VELOCIDAD_EMPUJE_POR_NEWTON = 1.5
"""cm/s por newton: velocidad pedida a un dedo frenado para que el motor entregue su fuerza completa."""
FUERZA_BRAZO_MAXIMA = 100.0 * NEWTON
"""Fuerza con la que el brazo empuja la base de la pinza hacia la pose pedida: si algo la frena (una cabeza de caballo debajo de un
dedo), la pinza se queda atrás en vez de atravesarlo. ESTIMADO."""
FUERZA_SOSTEN_N = 60.0
"""Fuerza con la que cada dedo se queda quieto una vez en su posición (no es la de agarre): no se abre por inercia. ESTIMADO."""
PASOS_VENTANA = 24
"""Pasos de física (0,1 s) sobre los que se mide si un dedo avanza."""
PASOS_ARRANQUE = 24
"""Pasos tras una orden en los que no se busca si un dedo está frenado (todavía está acelerando)."""


@dataclass(frozen=True)
class GeometriaTablero:
    """Dónde está el tablero en el mundo (mm), deducido de las posiciones calibradas de las casillas."""

    origen_a1: tuple[float, float]
    paso_u: tuple[float, float]
    paso_v: tuple[float, float]
    z_superficie: float

    @classmethod
    def desde_posiciones(cls, posiciones: dict[str, tuple[float, float, float]], z_superficie: float) -> "GeometriaTablero":
        a1, h1, a8 = posiciones["a1"], posiciones["h1"], posiciones["a8"]
        return cls((a1[0], a1[1]), ((h1[0] - a1[0]) / 7, (h1[1] - a1[1]) / 7), ((a8[0] - a1[0]) / 7, (a8[1] - a1[1]) / 7), z_superficie)

    @property
    def angulo_u_grados(self) -> float:
        return math.degrees(math.atan2(self.paso_u[1], self.paso_u[0]))

    @property
    def paso_mm(self) -> float:
        return math.hypot(*self.paso_u)

    def centro_casilla(self, nombre: str) -> tuple[float, float]:
        cuadro = chess.parse_square(nombre)
        columna, fila = chess.square_file(cuadro), chess.square_rank(cuadro)
        return (
            self.origen_a1[0] + columna * self.paso_u[0] + fila * self.paso_v[0],
            self.origen_a1[1] + columna * self.paso_u[1] + fila * self.paso_v[1],
        )

    def coordenadas_tablero(self, x: float, y: float) -> tuple[float, float]:
        """`(columna, fila)` fraccionarias (0 = centro de a1) de un punto del mundo."""
        dx, dy = x - self.origen_a1[0], y - self.origen_a1[1]
        determinante = self.paso_u[0] * self.paso_v[1] - self.paso_u[1] * self.paso_v[0]
        return (
            (dx * self.paso_v[1] - dy * self.paso_v[0]) / determinante,
            (self.paso_u[0] * dy - self.paso_u[1] * dx) / determinante,
        )

    def casilla_en(self, x: float, y: float) -> str | None:
        columna, fila = self.coordenadas_tablero(x, y)
        columna, fila = round(columna), round(fila)
        return chess.square_name(chess.square(columna, fila)) if 0 <= columna < 8 and 0 <= fila < 8 else None


@dataclass
class EstadoPieza:
    """Lo que el resto del simulador necesita saber de una pieza."""

    identificador: int
    simbolo: str
    x: float
    y: float
    z: float
    inclinacion_grados: float
    casilla_inicial: str
    yaw_grados: float = 0.0

    @property
    def tipo(self) -> str:
        return self.simbolo.lower()


def piezas_de_fen(fen: str) -> list[tuple[str, str]]:
    """`(casilla, símbolo)` de cada pieza del FEN."""
    tablero = chess.Board(fen)
    return [(chess.square_name(c), p.symbol()) for c, p in tablero.piece_map().items()]


class MundoFisico:
    """Escena PyBullet con el tablero, las piezas y la pinza."""

    def __init__(self, geometria: GeometriaTablero, fisicos: ParametrosFisicos, fen: str, yaw_inicial_grados: float, punta_inicial: tuple[float, float, float]):
        import pybullet as p

        self._p = p
        self.geometria, self.fisicos = geometria, fisicos
        self.cliente = p.connect(p.DIRECT)
        p.setGravity(0, 0, -981.0, physicsClientId=self.cliente)
        p.setPhysicsEngineParameter(
            fixedTimeStep=fisicos.paso_s, numSolverIterations=200, numSubSteps=1, enableConeFriction=1, physicsClientId=self.cliente
        )
        self._friccion_dedos = fisicos.friccion_dedos
        self._ids_piezas: dict[int, tuple[str, str]] = {}
        self._aflojar_hasta_paso = 0
        self._paso = 0
        self._empujando: dict[int, float | None] = {0: None, 1: None}
        self._historia = {0: deque(maxlen=PASOS_VENTANA + 1), 1: deque(maxlen=PASOS_VENTANA + 1)}
        self._paso_orden = 0
        self._fuerza_n = 10.0
        self._crear_tablero()
        self._crear_pinza(punta_inicial, yaw_inicial_grados)
        self.cargar_fen(fen)

    # --- construcción ------------------------------------------------------------------------------------------------
    def _forma_caja(self, ancho_x: float, ancho_y: float, alto: float, centro: tuple[float, float, float]) -> int:
        return self._p.createCollisionShape(
            self._p.GEOM_BOX, halfExtents=[ancho_x * MM / 2, ancho_y * MM / 2, alto * MM / 2], collisionFramePosition=[c * MM for c in centro],
            physicsClientId=self.cliente,
        )

    def _crear_tablero(self) -> None:
        p, g, f = self._p, self.geometria, self.fisicos
        z_superficie = g.z_superficie * MM
        mesa = p.createCollisionShape(p.GEOM_BOX, halfExtents=[200, 200, 5], physicsClientId=self.cliente)
        self.mesa = p.createMultiBody(0, mesa, basePosition=[g.origen_a1[0] * MM, g.origen_a1[1] * MM, z_superficie - f.grosor_tablero_mm * MM - 5], physicsClientId=self.cliente)
        mitad_u, mitad_v = 4 * g.paso_mm + f.borde_tablero_mm, 4 * math.hypot(*g.paso_v) + f.borde_tablero_mm
        forma = p.createCollisionShape(p.GEOM_BOX, halfExtents=[mitad_u * MM, mitad_v * MM, f.grosor_tablero_mm * MM / 2], physicsClientId=self.cliente)
        centro = self.geometria.origen_a1[0] + 3.5 * (g.paso_u[0] + g.paso_v[0]), self.geometria.origen_a1[1] + 3.5 * (g.paso_u[1] + g.paso_v[1])
        orientacion = p.getQuaternionFromEuler([0, 0, math.radians(g.angulo_u_grados)])
        self.tablero = p.createMultiBody(
            0, forma, basePosition=[centro[0] * MM, centro[1] * MM, z_superficie - f.grosor_tablero_mm * MM / 2], baseOrientation=orientacion, physicsClientId=self.cliente
        )
        for cuerpo in (self.mesa, self.tablero):
            p.changeDynamics(cuerpo, -1, lateralFriction=f.friccion_tablero, restitution=0.0, physicsClientId=self.cliente)

    def _crear_pinza(self, punta: tuple[float, float, float], yaw_grados: float) -> None:
        p, f = self._p, self.fisicos
        largo, ancho, grosor = f.dedo_largo_mm, f.dedo_ancho_mm, f.dedo_grosor_mm
        palma = self._forma_caja(f.palma_ancho_mm, f.palma_ancho_mm, f.palma_alto_mm, (0, 0, largo + f.palma_alto_mm / 2))
        dedo = p.createCollisionShape(p.GEOM_BOX, halfExtents=[grosor * MM / 2, ancho * MM / 2, largo * MM / 2], physicsClientId=self.cliente)
        posiciones = [[-grosor * MM / 2, 0, largo * MM / 2], [grosor * MM / 2, 0, largo * MM / 2]]
        orientacion = p.getQuaternionFromEuler([0, 0, math.radians(yaw_grados)])
        self.pinza = p.createMultiBody(
            baseMass=300.0, baseCollisionShapeIndex=palma, basePosition=[c * MM for c in punta], baseOrientation=orientacion,
            linkMasses=[80.0, 80.0], linkCollisionShapeIndices=[dedo, dedo], linkVisualShapeIndices=[-1, -1],
            linkPositions=posiciones, linkOrientations=[[0, 0, 0, 1]] * 2, linkInertialFramePositions=[[0, 0, 0]] * 2,
            linkInertialFrameOrientations=[[0, 0, 0, 1]] * 2, linkParentIndices=[0, 0],
            linkJointTypes=[p.JOINT_PRISMATIC, p.JOINT_PRISMATIC], linkJointAxis=[[-1, 0, 0], [1, 0, 0]], physicsClientId=self.cliente,
        )
        for dedo_id in (0, 1):
            p.changeDynamics(
                self.pinza, dedo_id, lateralFriction=self._friccion_dedos, restitution=0.0, jointLowerLimit=0.0,
                jointUpperLimit=f.carrera_mm / 2 * MM, activationState=p.ACTIVATION_STATE_DISABLE_SLEEPING, physicsClientId=self.cliente,
            )
        p.changeDynamics(
            self.pinza, -1, lateralFriction=self._friccion_dedos, restitution=0.0,
            activationState=p.ACTIVATION_STATE_DISABLE_SLEEPING, physicsClientId=self.cliente,
        )
        self._restriccion = p.createConstraint(
            self.pinza, -1, -1, -1, p.JOINT_FIXED, [0, 0, 0], [0, 0, 0], [c * MM for c in punta], childFrameOrientation=orientacion, physicsClientId=self.cliente
        )
        p.changeConstraint(self._restriccion, maxForce=FUERZA_BRAZO_MAXIMA, erp=1.0, physicsClientId=self.cliente)
        for dedo_id in (0, 1):
            p.resetJointState(self.pinza, dedo_id, f.carrera_mm / 2 * MM, physicsClientId=self.cliente)
        self.fijar_dedos(f.carrera_mm, 20.0, f.velocidad_dedos_max_mm_s)
        self._punta, self._yaw = punta, yaw_grados

    def _crear_pieza(self, casilla: str, simbolo: str) -> int:
        p, f = self._p, self.fisicos
        perfil: PerfilPieza = PERFILES_PIEZAS[simbolo.lower()]
        centro_masa = perfil.alto_mm * 0.38
        compuesta = p.createCollisionShapeArray(
            [self._tipo_forma(s) for s in perfil.segmentos], radii=[(s.ancho_x * MM / 2) for s in perfil.segmentos],
            halfExtents=[[s.ancho_x * MM / 2, (s.ancho_y or s.ancho_x) * MM / 2, (s.z_superior - s.z_inferior) * MM / 2] for s in perfil.segmentos],
            lengths=[(s.z_superior - s.z_inferior) * MM for s in perfil.segmentos],
            collisionFramePositions=[[0, 0, ((s.z_inferior + s.z_superior) / 2 - centro_masa) * MM] for s in perfil.segmentos], physicsClientId=self.cliente,
        )
        x, y = self.geometria.centro_casilla(casilla)
        mira_adelante = 0.0 if simbolo.isupper() else 180.0
        yaw = math.radians(self.geometria.angulo_u_grados + 90.0 + mira_adelante)
        cuerpo = p.createMultiBody(
            baseMass=perfil.masa_g, baseCollisionShapeIndex=compuesta,
            basePosition=[x * MM, y * MM, (self.geometria.z_superficie + centro_masa) * MM + 0.005],
            baseOrientation=p.getQuaternionFromEuler([0, 0, yaw]),
            physicsClientId=self.cliente,
        )
        p.changeDynamics(
            cuerpo, -1, lateralFriction=f.friccion_piezas, spinningFriction=0.05, restitution=0.0, linearDamping=0.2, angularDamping=0.2, physicsClientId=self.cliente
        )
        return cuerpo

    def _tipo_forma(self, segmento) -> int:
        return self._p.GEOM_CYLINDER if segmento.ancho_y is None else self._p.GEOM_BOX

    def cargar_fen(self, fen: str) -> None:
        """Reemplaza todas las piezas por las del FEN, apoyadas en sus casillas."""
        for cuerpo in list(self._ids_piezas):
            self._p.removeBody(cuerpo, physicsClientId=self.cliente)
        self._ids_piezas.clear()
        for casilla, simbolo in piezas_de_fen(fen):
            self._ids_piezas[self._crear_pieza(casilla, simbolo)] = (simbolo, casilla)
        self.avanzar(30)

    # --- comandos ----------------------------------------------------------------------------------------------------
    def fijar_herramienta(self, punta: tuple[float, float, float], yaw_grados: float) -> None:
        """Lleva la base de la pinza a `punta` (mm, el centro de las puntas de los dedos) con los dedos cerrando en la dirección `yaw_grados`."""
        p = self._p
        p.changeConstraint(
            self._restriccion, [c * MM for c in punta], jointChildFrameOrientation=p.getQuaternionFromEuler([0, 0, math.radians(yaw_grados)]),
            maxForce=FUERZA_BRAZO_MAXIMA, erp=1.0, physicsClientId=self.cliente,
        )
        self._punta, self._yaw = punta, yaw_grados

    def fijar_dedos(self, ancho_mm: float, fuerza_total_n: float, velocidad_mm_s: float) -> None:
        """Ordena abrir o cerrar los dedos hasta `ancho_mm` entre ellos, empujando con `fuerza_total_n` (repartida entre los dos)."""
        self._ancho_objetivo_mm, self._fuerza_n, self._velocidad_dedos = ancho_mm, fuerza_total_n, velocidad_mm_s
        self._empujando = {0: None, 1: None}
        self._paso_orden = self._paso
        self._aplicar_motores()

    def _aplicar_motores(self) -> None:
        """Mueve los dedos a la velocidad pedida; si un dedo se frena contra una pieza, lo empuja con toda la fuerza configurada.

        El motor de velocidad de PyBullet solo entrega fuerza en proporción a cuánto le falta de velocidad, así que un dedo frenado se
        detecta por su falta de avance y se le pide una velocidad alta (la fuerza queda limitada por `force`).
        """
        p = self._p
        aflojado = self._paso < self._aflojar_hasta_paso
        fuerza_cada_dedo = 0.0 if aflojado else self._fuerza_n / 2
        maxima = self._velocidad_dedos / 2 * MM
        for dedo_id in (0, 1):
            posicion = p.getJointState(self.pinza, dedo_id, physicsClientId=self.cliente)[0]
            historia = self._historia[dedo_id]
            historia.append(posicion)
            objetivo = self._ancho_objetivo_mm / 2 * MM
            error = objetivo - posicion
            velocidad = max(-maxima, min(maxima, error * GANANCIA_DEDOS))
            if abs(error) <= TOLERANCIA_DEDOS:
                self._empujando[dedo_id] = None
            elif self._empujando[dedo_id] is None and self._paso - self._paso_orden > PASOS_ARRANQUE and len(historia) == historia.maxlen:
                avance = abs(historia[-1] - historia[0])
                if avance < 0.25 * maxima * PASOS_VENTANA * self.fisicos.paso_s and avance < 0.015:
                    self._empujando[dedo_id] = posicion
            if self._empujando[dedo_id] is not None:
                if abs(posicion - self._empujando[dedo_id]) > 0.15:
                    self._empujando[dedo_id] = None
                else:
                    velocidad = math.copysign(fuerza_cada_dedo * VELOCIDAD_EMPUJE_POR_NEWTON, error)
            sostenido = abs(error) <= TOLERANCIA_DEDOS and not aflojado
            fuerza = max(fuerza_cada_dedo, FUERZA_SOSTEN_N) if sostenido else fuerza_cada_dedo
            p.setJointMotorControl2(self.pinza, dedo_id, p.VELOCITY_CONTROL, targetVelocity=velocidad, force=fuerza * NEWTON, physicsClientId=self.cliente)

    def aflojar_dedos(self, segundos: float) -> None:
        """Fallo: los dedos dejan de empujar un rato (la pieza apretada se cae)."""
        self._aflojar_hasta_paso = self._paso + int(segundos / self.fisicos.paso_s)
        self._aplicar_motores()

    def fijar_friccion_dedos(self, friccion: float) -> None:
        for dedo_id in (-1, 0, 1):
            self._p.changeDynamics(self.pinza, dedo_id, lateralFriction=friccion, physicsClientId=self.cliente)

    def avanzar(self, pasos: int = 1) -> None:
        """Da `pasos` pasos de física."""
        for _ in range(pasos):
            self._aplicar_motores()
            self._p.stepSimulation(physicsClientId=self.cliente)
            self._paso += 1

    # --- lectura -----------------------------------------------------------------------------------------------------
    def desviacion_herramienta_mm(self) -> float:
        """Distancia entre donde el brazo pide la pinza y donde está: distinta de cero si choca con algo."""
        posicion = self._p.getBasePositionAndOrientation(self.pinza, physicsClientId=self.cliente)[0]
        return math.dist([c / MM for c in posicion], self._punta)

    def estado_dedos(self) -> tuple[float, float]:
        """`(ancho entre dedos en mm, velocidad de cambio del ancho en mm/s)`."""
        a, b = (self._p.getJointState(self.pinza, i, physicsClientId=self.cliente) for i in (0, 1))
        return (a[0] + b[0]) / MM, (a[1] + b[1]) / MM

    def fuerza_de_contacto_con_piezas_n(self) -> float:
        """Suma de las fuerzas normales entre los dedos y cualquier pieza, en newtons."""
        total = 0.0
        for contacto in self._p.getContactPoints(bodyA=self.pinza, physicsClientId=self.cliente):
            if contacto[2] in self._ids_piezas and contacto[3] in (0, 1):
                total += contacto[9]
        return total / NEWTON

    def fuerzas_por_pieza_y_dedo_n(self) -> dict[tuple[int, int], float]:
        """Fuerza normal, en newtons, de cada par (pieza, dedo) en contacto."""
        fuerzas: dict[tuple[int, int], float] = {}
        for contacto in self._p.getContactPoints(bodyA=self.pinza, physicsClientId=self.cliente):
            if contacto[2] in self._ids_piezas and contacto[3] in (0, 1):
                clave = (contacto[2], contacto[3])
                fuerzas[clave] = fuerzas.get(clave, 0.0) + contacto[9] / NEWTON
        return fuerzas

    def piezas(self) -> list[EstadoPieza]:
        resultado = []
        for cuerpo, (simbolo, casilla) in self._ids_piezas.items():
            posicion, orientacion = self._p.getBasePositionAndOrientation(cuerpo, physicsClientId=self.cliente)
            eje_z = self._p.getMatrixFromQuaternion(orientacion)[8]
            resultado.append(
                EstadoPieza(
                    cuerpo, simbolo, posicion[0] / MM, posicion[1] / MM, posicion[2] / MM - PERFILES_PIEZAS[simbolo.lower()].alto_mm * 0.38,
                    math.degrees(math.acos(max(-1.0, min(1.0, eje_z)))), casilla,
                    math.degrees(self._p.getEulerFromQuaternion(orientacion)[2]),
                )
            )
        return resultado

    def cerrar(self) -> None:
        """Desconecta de PyBullet."""
        if self.cliente >= 0:
            try:
                self._p.disconnect(physicsClientId=self.cliente)
            finally:
                self.cliente = -1


class MundoGeometrico:
    """Mundo sin física: dedos con la misma interfaz, y una pieza entre ellos al cerrar se considera apretada y acompaña a la herramienta."""

    def __init__(self, geometria: GeometriaTablero, fisicos: ParametrosFisicos, fen: str, yaw_inicial_grados: float, punta_inicial: tuple[float, float, float]):
        self.geometria, self.fisicos = geometria, fisicos
        self._punta, self._yaw = punta_inicial, yaw_inicial_grados
        self._ancho, self._objetivo, self._velocidad, self._velocidad_instantanea = fisicos.carrera_mm, fisicos.carrera_mm, 40.0, 0.0
        self._piezas: dict[int, EstadoPieza] = {}
        self._sostenida: int | None = None
        self._desplazamiento_sostenida = (0.0, 0.0)
        self.cargar_fen(fen)

    def cargar_fen(self, fen: str) -> None:
        self._piezas.clear()
        self._sostenida = None
        for numero, (casilla, simbolo) in enumerate(piezas_de_fen(fen), start=1):
            x, y = self.geometria.centro_casilla(casilla)
            self._piezas[numero] = EstadoPieza(numero, simbolo, x, y, self.geometria.z_superficie, 0.0, casilla)

    def fijar_herramienta(self, punta: tuple[float, float, float], yaw_grados: float) -> None:
        self._punta, self._yaw = punta, yaw_grados
        if self._sostenida is not None:
            pieza = self._piezas[self._sostenida]
            pieza.x, pieza.y = punta[0] + self._desplazamiento_sostenida[0], punta[1] + self._desplazamiento_sostenida[1]
            pieza.z = max(self.geometria.z_superficie, punta[2])

    def fijar_dedos(self, ancho_mm: float, fuerza_total_n: float, velocidad_mm_s: float) -> None:
        self._objetivo, self._velocidad = ancho_mm, velocidad_mm_s

    def aflojar_dedos(self, segundos: float) -> None:
        self._sostenida = None

    def fijar_friccion_dedos(self, friccion: float) -> None:
        pass

    def _pieza_entre_dedos(self) -> EstadoPieza | None:
        for pieza in self._piezas.values():
            if math.hypot(pieza.x - self._punta[0], pieza.y - self._punta[1]) < 4.0 and abs(pieza.z - self._punta[2]) < 12.0:
                return pieza
        return None

    def avanzar(self, pasos: int = 1) -> None:
        paso = self.fisicos.paso_s * pasos
        faltante = self._objetivo - self._ancho
        avance = max(-self._velocidad * paso, min(self._velocidad * paso, faltante))
        pieza = self._pieza_entre_dedos() if avance < 0 or self._sostenida is not None else None
        ancho_pieza = PERFILES_PIEZAS[pieza.tipo].ancho_base_mm if pieza else 0.0
        self._velocidad_instantanea = avance / paso if paso else 0.0
        if pieza is not None and self._ancho + avance <= ancho_pieza:
            self._ancho = ancho_pieza
            self._velocidad_instantanea = 0.0
            if self._sostenida is None:
                self._sostenida = pieza.identificador
                self._desplazamiento_sostenida = (pieza.x - self._punta[0], pieza.y - self._punta[1])
        else:
            self._ancho += avance
            if self._sostenida is not None and self._ancho > ancho_pieza + 0.3:
                self._sostenida = None

    def desviacion_herramienta_mm(self) -> float:
        return 0.0

    def estado_dedos(self) -> tuple[float, float]:
        return self._ancho, self._velocidad_instantanea

    def fuerza_de_contacto_con_piezas_n(self) -> float:
        return 10.0 if self._sostenida is not None else 0.0

    def fuerzas_por_pieza_y_dedo_n(self) -> dict[tuple[int, int], float]:
        return {}

    def piezas(self) -> list[EstadoPieza]:
        return list(self._piezas.values())

    def cerrar(self) -> None:
        pass
