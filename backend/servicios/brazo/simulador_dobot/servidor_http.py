"""Servidor HTTP del simulador: sirve `web/index.html` (respaldo) y la API JSON que usa el front React (con CORS), sin dependencias.

Las rutas están listadas en `docs/simulador_brazo.md`. Los errores son siempre `{"error": "mensaje"}` con código 4xx o 5xx.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.servicios.brazo.simulador_dobot.nucleo import Simulador
from backend.servicios.brazo.simulador_dobot.tareas import ErrorApi, GestorTareas

CARPETA_WEB = Path(__file__).resolve().parent / "web"
CABECERAS_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class _Manejador(BaseHTTPRequestHandler):
    server: "ServidorWeb"

    def log_message(self, formato, *argumentos) -> None:  # el log HTTP ensucia la consola
        pass

    def _responder(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        for nombre, valor in CABECERAS_CORS.items():
            self.send_header(nombre, valor)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo: int = 200) -> None:
        self._responder(codigo, json.dumps(datos).encode("utf-8"), "application/json; charset=utf-8")

    def _ruta(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    def do_OPTIONS(self) -> None:
        self._responder(204, b"", "text/plain")

    def do_GET(self) -> None:
        ruta, servidor = self._ruta(), self.server
        try:
            if ruta in ("/", "/index.html"):
                self._responder(200, (CARPETA_WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif ruta == "/api/estado":
                self._json(servidor.estado())
            elif ruta == "/api/parametros":
                self._json(servidor.parametros())
            else:
                self._json({"error": "no existe"}, 404)
        except ErrorApi as error:
            self._json({"error": error.mensaje}, error.codigo)
        except Exception as error:
            self._json({"error": f"error interno: {type(error).__name__}: {error}"}, 500)

    def do_POST(self) -> None:
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
            if not isinstance(datos, dict):
                raise ValueError
        except ValueError:
            return self._json({"error": "JSON inválido: se esperaba un objeto"}, 400)
        try:
            codigo, respuesta = self.server.atender(self._ruta(), datos)
        except ErrorApi as error:
            return self._json({"error": error.mensaje}, error.codigo)
        except ValueError as error:
            return self._json({"error": str(error)}, 400)
        except Exception as error:
            return self._json({"error": f"error interno: {type(error).__name__}: {error}"}, 500)
        self._json(respuesta, codigo)


class ServidorWeb(ThreadingHTTPServer):
    """Sirve la API en `(host, puerto)`; con puerto 0 el sistema elige uno libre.

    `puerto_dashboard` es el del servidor TCP del mismo simulador: las operaciones largas (jugada, pinza, ajuste de apertura) se conectan a
    él como clientes. Sin él, esas rutas responden 503 y el resto funciona.
    """

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, simulador: Simulador, host: str = "127.0.0.1", puerto: int = 8765, puerto_dashboard: int | None = None):
        self.simulador = simulador
        self.tareas = GestorTareas(simulador, puerto_dashboard)
        super().__init__((host, puerto), _Manejador)

    @property
    def puerto(self) -> int:
        return self.server_address[1]

    # --- lectura ----------------------------------------------------------------------------------------------------------
    def estado(self) -> dict:
        estado = self.simulador.instantanea()
        resumen = self.tareas.resumen()
        estado["tarea"], estado["apertura"] = resumen["tarea"], resumen["apertura"]
        if resumen["apertura"] is not None:
            estado["apertura_actual"] = resumen["apertura"]["apertura"]
        return estado

    def parametros(self) -> dict:
        planos = self.simulador.parametros_agarre_dict()
        a = self.simulador.agarre
        extra = {"aperturas_efectivas": {t: _apertura_o_none(a, t) for t in "pnbrqk"}, "archivo": str(self.simulador.ruta_persistencia or "")}
        return {**planos, **extra, "parametros": planos}

    # --- escritura --------------------------------------------------------------------------------------------------------
    def atender(self, ruta: str, d: dict) -> tuple[int, dict]:
        sim, tareas = self.simulador, self.tareas
        if ruta == "/api/reiniciar":
            tareas.cancelar_todo()
            sim.reiniciar(d.get("fen") or None)
        elif ruta == "/api/fen":
            tareas.cancelar_todo()
            sim.cargar_fen(str(d.get("fen", "")))
        elif ruta == "/api/pausa":
            sim.pausado = bool(d.get("pausado", not sim.pausado))
        elif ruta == "/api/velocidad":
            sim.escala_tiempo = max(0.1, min(20.0, float(d.get("escala", 1.0))))
        elif ruta == "/api/fallo":
            sim.inyectar_fallo(str(d.get("tipo", "")), d.get("valor", True))
        elif ruta == "/api/limpiar_log":
            sim.log.clear()
        elif ruta == "/api/jugada":
            return 202, {"ok": True, **tareas.iniciar_jugada(
                str(d.get("uci", "")), str(d.get("modo", "completa")), d.get("fuerza"), d.get("margen_agarre"), d.get("velocidad"))}
        elif ruta == "/api/ensayo":
            return 200, tareas.ensayo(str(d.get("uci", "")))
        elif ruta == "/api/continuar":
            return 200, {"ok": True, **tareas.continuar()}
        elif ruta == "/api/cancelar":
            return 200, {"ok": True, **tareas.cancelar()}
        elif ruta == "/api/pinza":
            return 200, tareas.pinza(str(d.get("accion", "")), d.get("valor"), d.get("fuerza"))
        elif ruta == "/api/pieza_en_pinza":
            return 200, tareas.pieza_en_pinza(d.get("tipo"))
        elif ruta == "/api/jog":
            return 200, tareas.jog(d.get("dx", 0), d.get("dy", 0), d.get("dz", 0))
        elif ruta == "/api/parametros":
            tareas._exigir_sin_tarea()
            planos = sim.actualizar_parametros(d)
            return 200, {"ok": True, **planos, "parametros": planos}
        elif ruta == "/api/apertura/iniciar":
            return 202, {"ok": True, **tareas.apertura_iniciar(d.get("pieza"), d.get("inicial"), d.get("casilla"), d.get("velocidad"))}
        elif ruta == "/api/apertura/mover":
            return 200, {"ok": True, **tareas.apertura_mover(d.get("valor"), d.get("delta"))}
        elif ruta == "/api/apertura/guardar":
            return 200, tareas.apertura_guardar(d.get("holgura"))
        elif ruta == "/api/apertura/terminar":
            return 200, {"ok": True, **tareas.apertura_terminar()}
        else:
            raise ErrorApi(404, "no existe")
        return 200, {"ok": True}

    def iniciar(self) -> None:
        threading.Thread(target=self.serve_forever, name="http-simulador", daemon=True).start()

    def detener(self) -> None:
        self.tareas.cancelar_todo()
        self.shutdown()
        self.server_close()


def _apertura_o_none(agarre, tipo: str) -> int | None:
    try:
        return agarre.apertura_para(tipo)
    except RuntimeError:
        return None
