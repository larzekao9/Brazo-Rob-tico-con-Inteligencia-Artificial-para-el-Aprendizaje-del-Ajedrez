"""Servidor HTTP del front del simulador: sirve `web/index.html` y una API JSON mínima (sin dependencias)."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.servicios.brazo.simulador_dobot.nucleo import Simulador

CARPETA_WEB = Path(__file__).resolve().parent / "web"


class _Manejador(BaseHTTPRequestHandler):
    server: "ServidorWeb"

    def log_message(self, formato, *argumentos) -> None:  # el log HTTP ensucia la consola
        pass

    def _responder(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo: int = 200) -> None:
        self._responder(codigo, json.dumps(datos).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._responder(200, (CARPETA_WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/estado":
            self._json(self.server.simulador.instantanea())
        else:
            self._json({"error": "no existe"}, 404)

    def do_POST(self) -> None:
        sim = self.server.simulador
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "JSON inválido"}, 400)
        try:
            if self.path == "/api/reiniciar":
                sim.reiniciar(datos.get("fen") or None)
            elif self.path == "/api/fen":
                sim.cargar_fen(str(datos.get("fen", "")))
            elif self.path == "/api/pausa":
                sim.pausado = bool(datos.get("pausado", not sim.pausado))
            elif self.path == "/api/velocidad":
                sim.escala_tiempo = max(0.1, min(20.0, float(datos.get("escala", 1.0))))
            elif self.path == "/api/fallo":
                sim.inyectar_fallo(str(datos.get("tipo", "")), datos.get("valor", True))
            elif self.path == "/api/limpiar_log":
                sim.log.clear()
            else:
                return self._json({"error": "no existe"}, 404)
        except ValueError as error:
            return self._json({"error": str(error)}, 400)
        self._json({"ok": True})


class ServidorWeb(ThreadingHTTPServer):
    """Sirve el front en `(host, puerto)`; con puerto 0 el sistema elige uno libre."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, simulador: Simulador, host: str = "127.0.0.1", puerto: int = 8765):
        self.simulador = simulador
        super().__init__((host, puerto), _Manejador)

    @property
    def puerto(self) -> int:
        return self.server_address[1]

    def iniciar(self) -> None:
        threading.Thread(target=self.serve_forever, name="http-simulador", daemon=True).start()

    def detener(self) -> None:
        self.shutdown()
        self.server_close()
