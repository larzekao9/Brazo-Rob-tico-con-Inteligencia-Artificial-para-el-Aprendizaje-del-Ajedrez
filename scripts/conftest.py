"""Configuración global de pytest para scripts/ — mismo patrón que backend/conftest.py."""
import os

os.environ["PYTEST_RUNNING"] = "1"
os.environ.pop("DATABASE_URL", None)
