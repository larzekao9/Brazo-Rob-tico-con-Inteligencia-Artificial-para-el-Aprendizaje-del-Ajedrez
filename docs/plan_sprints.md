# Plan de implementación por sprint

Basado en `PLAN_IMPLEMENTACION_COMPLETO.md` (secciones 7 a 11) y en el Product Backlog de 11
Historias de Usuario (51 puntos totales) definido junto con la documentación de SW2 y Taller
de Grado I. Reemplaza la versión anterior de este archivo, que estaba basada en un borrador
previo del plan (por área, sin las 11 HU balanceadas).

---

## Sprint 1 — Núcleo técnico

**Objetivo:** motor de ajedrez respondiendo jugadas de forma aislada, reconocimiento de
tablero funcionando sobre fotos de prueba, y el pipeline de datos corriendo de punta a punta.

| HU | Descripción | Puntos | Responsable | Estado |
|---|---|---|---|---|
| HU2 | Motor de Jugadas y Niveles de Dificultad | 3 | Hebert | ✅ Hecho |
| HU1 | Reconocimiento de Tablero y Piezas | 8 | Hebert | ⬜ Pendiente |
| HU3 | Entrenamiento del Modelo con Partidas de Referencia | 5 | Luis Ángel | 🟨 En curso |

### HU2 — Motor (Hebert) — ✅ Hecho
- [x] Stockfish instalado y probado desde `python-chess`.
- [x] `backend/engine/stockfish_wrapper.py`: `calcular_jugada(fen, nivel)`,
      `analizar_posicion(fen, nivel)` (evaluación en centipawns + mate), `obtener_variaciones`
      (mejores jugadas candidatas vía MultiPV) — esto último adelanta trabajo útil para HU6.
- [x] Tests con posiciones conocidas (aperturas + mate en 1).
- [x] Expuesto vía `POST /jugada` y `POST /analisis` en el backend.

### HU3 — Modelo (Luis Ángel) — 🟨 En curso
- [x] Un mes de partidas de Lichess descargado (2017-02, 1.8 GB comprimido; el pipeline lee
      en streaming, no hace falta descomprimir entero).
- [x] `training/data_pipeline.py`: `board_to_tensor` y `pgn_to_samples` — validado localmente
      con partidas sintéticas y reales.
- [ ] Correr el pipeline en Google Colab con 100-200 partidas antes de escalar al mes
      completo (paso pendiente antes de dar por cerrada la HU).
- [ ] Primera versión entrenada del modelo, guardada en Google Drive.

### HU1 — Visión (Hebert) — ⬜ Pendiente
- [ ] Set de 15-20 fotos de tablero (luz y ángulo variados).
- [ ] Detección de las 64 casillas (transformación de perspectiva + grilla, OpenCV).
- [ ] Clasificación de pieza por casilla.
- [ ] `reconocer_tablero(imagen) -> fen`.

**Definition of Done Sprint 1:** `calcular_jugada` en verde (cumplido); `data_pipeline.py`
corre sobre 100-200 partidas reales en Colab sin errores; `reconocer_tablero` reconoce
correctamente al menos un tablero de prueba fijo.

---

## Sprint 2 — Interfaz, aprendizaje y configuración

**Objetivo:** visualizar en tiempo real lo que el sistema percibe y decide, primer modelo
entrenado con evaluación real, modo educativo básico, y configuración de partida.

| HU | Descripción | Puntos | Responsable |
|---|---|---|---|
| HU6 | Visualización del Razonamiento en Tiempo Real | 5 | Hebert |
| HU4 | Reentrenamiento y Evaluación del Modelo | 5 | Luis Ángel |
| HU5 | Modo Educativo | 5 | Luis Ángel |
| HU10 | Configuración de Partida | 3 | Luis Ángel |

- [ ] HU6: interfaz que muestra la imagen capturada, el análisis de posición (ya disponible
      vía `analizar_posicion`/`obtener_variaciones`) y la jugada elegida.
- [ ] HU4: clasificación de patrones de error + reentrenamiento en lotes versionados +
      evaluación mediante partidas digitales simultáneas.
- [ ] HU5: explicación de jugadas y errores frecuentes, principios básicos del ajedrez.
- [ ] HU10: selección de nivel de dificultad y tipo de oponente desde la interfaz.

---

## Sprint 3 — Brazo robótico y cierre

**Objetivo:** interconexión con el brazo (simulado), rostro y expresiones, panel de
progreso, administración de sesiones, e integración completa para la defensa.

| HU | Descripción | Puntos | Responsable |
|---|---|---|---|
| HU9 | Interconexión con el Brazo Robótico | 8 | Hebert |
| HU7 | Rostro y Expresiones del Sistema | 3 | Luis Ángel |
| HU8 | Panel de Progreso | 3 | Luis Ángel |
| HU11 | Administración de Sesiones y Participantes | 3 | Luis Ángel |

### Sobre el simulador ya iniciado
Ya existe una versión temprana en `backend/simulation/escena.py` (escena de PyBullet con
tablero 3D estático y `resaltar_jugada(desde, hasta)`, sin cinemática inversa ni animación de
brazo — deliberadamente simple). Esto se adelantó mientras Visión estaba en pausa; queda como
base para HU9, pero la cinemática real y la conexión con el ESP32 son trabajo de este sprint,
no algo ya cerrado.

- [ ] HU9: cinemática inversa sobre el URDF del kit (o uno de referencia mientras se
      consigue el definitivo) + comunicación con el ESP32 real cuando esté disponible.
- [ ] HU7, HU8, HU11: interfaz y lógica de cada una.
- [ ] Integración de punta a punta con al menos 10 posiciones de prueba documentadas.
- [ ] Colchón de 2-3 días antes de la defensa para bugs de integración.

---

## Trabajo adelantado fuera del plan original

No estaba explícitamente en ninguna HU puntual, pero ya está construido y es una base útil
para varias historias (especialmente HU10 y HU11):

- `backend/models/partida.py`, `backend/game/servicio.py`, `backend/game/router.py`:
  partida jugable en memoria (`crear_partida`, `obtener_partida`, `mover`), expuesta vía
  `POST /partida`, `GET /partida/{id}`, `POST /partida/{id}/mover`.
- Tablero interactivo en React (`frontend/src/components/Tablero.jsx`).

**Pendiente conocido sobre esto:** el humano siempre juega blancas, no hay persistencia entre
reinicios del servidor, y la promoción de peón siempre es a dama. Ninguno bloquea la demo;
quedan para si sobra tiempo.

---

## Notas de seguimiento

- Marcar los checkboxes a medida que se completan las tareas — este archivo es el tablero de
  seguimiento; `PLAN_IMPLEMENTACION_COMPLETO.md` sigue siendo la fuente de verdad del alcance,
  la arquitectura y las reglas del proyecto.
- El contrato de datos entre módulos es FEN. Las jugadas se están devolviendo en notación SAN
  (más legible para mostrar en pantalla) — recordar convertir a UCI cuando HU9 necesite
  indicarle al brazo casillas de origen y destino (`python-chess` lo resuelve con
  `board.parse_san()` / `move.uci()`).
- Cualquier tarea que no se pueda completar en su sprint se avisa explícitamente antes de
  pasar al siguiente, no se arrastra en silencio.
- **Excepción acordada a la sección 2 y 5 de `PLAN_IMPLEMENTACION_COMPLETO.md`:** el backend no
  usa capas horizontales de primer nivel (`rutas/`, `servicios/`, `esquemas/`) ni nombres de
  carpeta en español (`motor/`, `simulacion/`) como se planteó ahí. Se mantiene la organización
  ya construida — módulos verticales por dominio (`backend/engine/`, `backend/game/`,
  `backend/models/`, `backend/simulation/`), cada uno con su propia lógica y router adentro,
  con nombres de funciones en español (`calcular_jugada`, `crear_partida`). Es una organización
  igualmente válida en FastAPI; para el "Diagrama de Paquetes por capas" de SW2 se documenta
  esta estructura tal cual está, en vez de reacomodar el código.
