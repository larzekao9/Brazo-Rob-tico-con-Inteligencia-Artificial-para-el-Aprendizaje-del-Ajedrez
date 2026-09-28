"""Constantes de nivel del modelo propio (Turing), sin dependencias pesadas.

Viven en un módulo aparte de `inferencia.py` a propósito: `inferencia` importa
`torch` al cargarse, y estas constantes las necesitan la fábrica de estrategias
(`fabrica_estrategias.py`) y el servicio de calibración, que no deben exigir
`torch` instalado (ver el import diferido en `EstrategiaModelo`).
"""

NIVEL_MAESTRO = 18
"""Desde este nivel (inclusive) el modelo juega a "maestro": determinista,
siempre la mejor candidata tras el filtro táctico. Por debajo, muestrea entre
sus candidatas."""

NIVEL_MAX_MODELO = NIVEL_MAESTRO
"""Techo de fuerza del modelo en la escala 0-20 del sistema. El modelo se
entrenó con partidas de ELO >= 2000, así que los niveles 19 y 20 juegan
exactamente igual que el 18. Stockfish, en cambio, sí usa la escala completa."""
