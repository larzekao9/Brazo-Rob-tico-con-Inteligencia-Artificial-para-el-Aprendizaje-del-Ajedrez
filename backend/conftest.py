"""Configuración global de pytest para el backend."""
import os

# Establece entorno de pruebas antes de importar cualquier módulo del backend
os.environ["PYTEST_RUNNING"] = "1"
os.environ.pop("DATABASE_URL", None)
