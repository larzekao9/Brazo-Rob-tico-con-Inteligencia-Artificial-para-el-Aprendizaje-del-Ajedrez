"""Emulador TCP/IP y Modbus del Dobot CR5AS y pinza DH-Robotics PGE-50-26.

Permite probar toda la lógica de control del brazo físico (`ClienteDobot`, `PinzaDH`,
`EjecutorReal`, scripts de calibración y partidas) de forma 100% virtual, sin necesidad
de estar conectado al hardware real.

Sigue el protocolo del controlador V4 (puerto 29999) y simula el canal interno Modbus RTU
(127.0.0.1:60000) respondiendo exactamente según el manual:
"Dobot TCP/IP Remote Control Interface Guide V4.6.5".
"""
from __future__ import annotations

import re
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from backend.servicios.brazo.calibracion_brazo import cargar_calibracion_brazo, cargar_parametros_agarre
from backend.servicios.brazo.pinza_dh import (
    AGARRE_LLEGO,
    AGARRE_SOSTIENE,
    REG_ESTADO_AGARRE,
    REG_ESTADO_INICIALIZACION,
    REG_FUERZA,
    REG_INICIALIZAR,
    REG_POSICION,
    REG_POSICION_ACTUAL,
    REG_VELOCIDAD,
)

PATRON_COMANDO = re.compile(r"^([a-zA-Z0-9_]+)\s*\((.*)\)\s*;?$")
PATRON_POSE = re.compile(r"pose\s*=\s*\{([^}]+)\}")
PATRON_JOINT = re.compile(r"joint\s*=\s*\{([^}]+)\}")


@dataclass
class EstadoBrazoVirtual:
    """Estado dinámico del robot virtual y su pinza."""

    modo: int = 5  # 5 = Habilitado y libre (ROBOT_MODE_ENABLE)
    velocidad_global: int = 20
    angulos_actuales: list[float] = field(default_factory=lambda: [302.85, 28.21, -149.12, 30.90, 89.71, -27.81])
    pose_actual: list[float] = field(default_factory=lambda: [-98.67, -664.06, 306.65, -180.0, 0.0, -120.0])
    
    # Registros virtuales Modbus de la pinza PGE-50-26
    registros_modbus: dict[int, int] = field(default_factory=lambda: {
        REG_INICIALIZAR: 1,
        REG_FUERZA: 20,
        REG_POSICION: 1000,
        REG_VELOCIDAD: 20,
        REG_ESTADO_INICIALIZACION: 1,
        REG_ESTADO_AGARRE: AGARRE_LLEGO,
        REG_POSICION_ACTUAL: 1000,
    })
    
    pieza_sostenida: bool = False
    historial_movimientos: list[str] = field(default_factory=list)


class EmuladorDobot:
    """Servidor TCP/IP local que emula un controlador Dobot CR5AS."""

    def __init__(self, host: str = "127.0.0.1", puerto: int = 29999):
        self.host = host
        self.puerto = puerto
        self.estado = EstadoBrazoVirtual()
        self._servidor: socket.socket | None = None
        self._hilo: threading.Thread | None = None
        self._activo = False
        self._clientes_conectados = 0
        self._cargar_calibracion_inicial()

    def _cargar_calibracion_inicial(self) -> None:
        calib = cargar_calibracion_brazo()
        if calib:
            self.estado.angulos_actuales = list(calib.angulos_cero)
            if "a1" in calib.posiciones_casillas:
                x, y, z = calib.posiciones_casillas["a1"]
                rx, ry, rz = calib.orientacion
                self.estado.pose_actual = [x, y, z + 80.0, rx, ry, rz]

    def iniciar(self) -> None:
        """Inicia el socket del servidor en un hilo secundario."""
        if self._activo:
            return
        self._servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._servidor.bind((self.host, self.puerto))
        self._servidor.listen(5)
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle_aceptar, daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        """Detiene el servidor y cierra sockets."""
        self._activo = False
        if self._servidor:
            try:
                self._servidor.close()
            except OSError:
                pass
            self._servidor = None

    def _bucle_aceptar(self) -> None:
        while self._activo and self._servidor:
            try:
                cliente_sock, _ = self._servidor.accept()
                self._clientes_conectados += 1
                t = threading.Thread(target=self._manejar_cliente, args=(cliente_sock,), daemon=True)
                t.start()
            except OSError:
                break

    def _manejar_cliente(self, sock: socket.socket) -> None:
        buffer = ""
        sock.settimeout(1.0)
        try:
            while self._activo:
                try:
                    datos = sock.recv(4096)
                    if not datos:
                        break
                    buffer += datos.decode("ascii", errors="ignore")
                    
                    while "(" in buffer and ")" in buffer:
                        idx_fin = buffer.find(")")
                        comando_raw = buffer[:idx_fin + 1].strip()
                        buffer = buffer[idx_fin + 1:].lstrip(";")
                        
                        respuesta = self.procesar_comando(comando_raw)
                        sock.sendall(respuesta.encode("ascii"))
                except socket.timeout:
                    continue
        finally:
            try:
                sock.close()
            except OSError:
                pass
            self._clientes_conectados = max(0, self._clientes_conectados - 1)

    def procesar_comando(self, raw: str) -> str:
        """Interpreta un comando Dobot y devuelve la respuesta en formato V4."""
        match = PATRON_COMANDO.match(raw.strip())
        if not match:
            return f"-10000,{{}},{raw};\n"
        
        nombre = match.group(1)
        params = match.group(2)
        nombre_lower = nombre.lower()

        # 1. Comandos de Estado y Control
        if nombre_lower == "robotmode":
            return f"0,{{{self.estado.modo}}},RobotMode();\n"
        
        if nombre_lower == "speedfactor":
            try:
                val = int(params.strip())
                self.estado.velocidad_global = val
            except ValueError:
                pass
            return f"0,{{}},SpeedFactor({params});\n"

        if nombre_lower in ("enablerobot", "poweron", "clearerror"):
            self.estado.modo = 5
            return f"0,{{}},{nombre}({params});\n"

        if nombre_lower == "disablerobot":
            self.estado.modo = 4
            return f"0,{{}},DisableRobot();\n"

        if nombre_lower == "geterrorid":
            return "0,{[]},GetErrorID();\n"

        # 2. Comandos de Herramienta y RS485 / Modbus
        if nombre_lower in ("settool485", "settoolpower", "settoolmode"):
            return f"0,{{}},{nombre}({params});\n"

        if nombre_lower == "modbuscreate":
            return f"0,{{0}},ModbusCreate({params});\n"

        if nombre_lower == "modbusclose":
            return f"0,{{}},ModbusClose({params});\n"

        if nombre_lower == "setholdregs":
            return self._manejar_set_hold_regs(params, raw)

        if nombre_lower == "getholdregs":
            return self._manejar_get_hold_regs(params, raw)

        # 3. Comandos de Consulta de Postura
        if nombre_lower == "getpose":
            p = self.estado.pose_actual
            valores = ",".join(f"{v:.4f}" for v in p)
            return f"0,{{{valores}}},GetPose();\n"

        if nombre_lower == "getangle":
            a = self.estado.angulos_actuales
            valores = ",".join(f"{v:.4f}" for v in a)
            return f"0,{{{valores}}},GetAngle();\n"

        # 4. Comandos de Movimiento
        if nombre_lower in ("movj", "movl"):
            return self._manejar_movimiento(nombre, params, raw)

        # Comando no implementado explícitamente pero aceptado
        return f"0,{{1}},{raw};\n"

    def _manejar_set_hold_regs(self, params: str, raw: str) -> str:
        """Simula la escritura de registros de la pinza DH PGE-50-26."""
        # Formato: SetHoldRegs(index, addr, count, {val1, val2}, valType)
        partes = [p.strip() for p in params.split(",", 3)]
        if len(partes) >= 3:
            try:
                addr = int(partes[1], 16) if partes[1].startswith("0x") else int(partes[1])
                match_vals = re.search(r"\{([^}]+)\}", params)
                if match_vals:
                    valores = [int(v.strip()) for v in match_vals.group(1).split(",")]
                    for i, val in enumerate(valores):
                        reg = addr + i
                        self.estado.registros_modbus[reg] = val

                        # Lógica de comportamiento de la pinza virtual
                        if reg == REG_POSICION:
                            self.estado.registros_modbus[REG_POSICION_ACTUAL] = val
                            # Si se cierra (<= 860) cerca de la altura de agarre, sostiene pieza
                            if val <= 860 and self.estado.pose_actual[2] <= 235.0:
                                self.estado.pieza_sostenida = True
                                self.estado.registros_modbus[REG_ESTADO_AGARRE] = AGARRE_SOSTIENE
                            else:
                                if val >= 950:
                                    self.estado.pieza_sostenida = False
                                self.estado.registros_modbus[REG_ESTADO_AGARRE] = AGARRE_LLEGO

                        elif reg == REG_INICIALIZAR and val == 1:
                            self.estado.registros_modbus[REG_ESTADO_INICIALIZACION] = 1
                            self.estado.registros_modbus[REG_ESTADO_AGARRE] = AGARRE_LLEGO
            except (ValueError, IndexError):
                pass
        return f"0,{{}},{raw};\n"

    def _manejar_get_hold_regs(self, params: str, raw: str) -> str:
        """Simula la lectura de registros de la pinza DH PGE-50-26."""
        # Formato: GetHoldRegs(index, addr, count, valType)
        partes = [p.strip() for p in params.split(",")]
        addr = 0x0200
        count = 1
        if len(partes) >= 2:
            try:
                addr = int(partes[1], 16) if partes[1].startswith("0x") else int(partes[1])
            except ValueError:
                pass
        if len(partes) >= 3:
            try:
                count = int(partes[2])
            except ValueError:
                pass

        respuestas = []
        for i in range(count):
            reg = addr + i
            respuestas.append(str(self.estado.registros_modbus.get(reg, 0)))

        valores_str = ",".join(respuestas)
        return f"0,{{{valores_str}}},GetHoldRegs({params});\n"

    def _manejar_movimiento(self, nombre: str, params: str, raw: str) -> str:
        """Actualiza la pose o ángulos actuales simulando el movimiento."""
        match_pose = PATRON_POSE.search(params)
        match_joint = PATRON_JOINT.search(params)

        if match_pose:
            try:
                coords = [float(v.strip()) for v in match_pose.group(1).split(",")]
                if len(coords) == 6:
                    self.estado.pose_actual = coords
                    self.estado.historial_movimientos.append(f"{nombre}_pose({coords})")
            except ValueError:
                pass
        elif match_joint:
            try:
                angs = [float(v.strip()) for v in match_joint.group(1).split(",")]
                if len(angs) == 6:
                    self.estado.angulos_actuales = angs
                    self.estado.historial_movimientos.append(f"{nombre}_joint({angs})")
            except ValueError:
                pass

        return f"0,{{1}},{raw};\n"


if __name__ == "__main__":
    emulador = EmuladorDobot("127.0.0.1", 29999)
    emulador.iniciar()
    print("Emulador Dobot CR5AS y Pinza PGE-50-26 iniciado en 127.0.0.1:29999.")
    print("Presiona Ctrl+C para finalizar.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        emulador.detener()
        print("Emulador detenido.")
