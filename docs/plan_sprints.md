# Plan de implementación por sprint

Basado en `PLAN_IMPLEMENTACION_COMPLETO.md` (secciones 13 a 16) y en el Product Backlog de 11
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
| HU1 | Reconocimiento de Tablero y Piezas | 8 | Hebert | ✅ Hecho |
| HU3 | Entrenamiento del Modelo con Partidas de Referencia | 5 | Luis Ángel | ✅ Hecho |

### HU2 — Motor (Hebert) — ✅ Hecho
- [x] Stockfish instalado y probado desde `python-chess`.
- [x] `backend/servicios/motor/motor_ajedrez.py`: `calcular_jugada(fen, nivel)`,
      `analizar_posicion(fen, nivel)` (evaluación en centipawns + mate), `obtener_variaciones`
      (mejores jugadas candidatas vía MultiPV) — esto último adelanta trabajo útil para HU6.
- [x] Tests con posiciones conocidas (aperturas + mate en 1).
- [x] Expuesto vía `POST /jugada` y `POST /analisis` en el backend.

### HU3 — Modelo (Luis Ángel) — ✅ Hecho
- [x] Un mes de partidas de Lichess descargado (2017-02, 1.8 GB comprimido; el pipeline lee
      en streaming, no hace falta descomprimir entero).
- [x] `training/data_pipeline.py`: `board_to_tensor` y `pgn_to_samples` — validado localmente
      con partidas sintéticas y reales.
- [x] `backend/servicios/aprendizaje/modelo_jugadas.py`: arquitectura de la CNN
      (`RedPrediccionJugadas`, 3 bloques conv+batchnorm+relu, sin pooling porque el tablero ya
      es 8x8) y `tensor_a_entrada_red` (permuta (8,8,12) -> (12,8,8)), compartidos entre
      entrenamiento e inferencia — mismo patrón que `modelo_piezas.py` de HU1. Test de forma en
      `backend/servicios/aprendizaje/test_modelo_jugadas.py` (se salta si no hay `torch`
      instalado localmente, como en esta máquina — el entrenamiento en sí corre en Colab).
- [x] `training/colab_entrenamiento.ipynb` creado: clona el repo, baja el PGN de
      database.lichess.org, arma un subconjunto de 200 partidas, entrena `RedPrediccionJugadas`
      unas pocas épocas y guarda el checkpoint versionado por fecha en Google Drive
      (`MyDrive/ajedrez_checkpoints/`).
- [x] Notebook ejecutado en Colab con GPU (2026-09-14): corrió de punta a punta sin errores.
- [x] Primera versión entrenada, guardada en Google Drive:
      `MyDrive/ajedrez_checkpoints/modelo_jugadas_v1_2026-09-14.pt` (200 partidas, 10 épocas).
      Accuracy de validación baja, como se esperaba con tan pocas partidas (ver nota en el
      notebook) — esta corrida valida el pipeline de punta a punta, no busca precisión todavía;
      escalar a más partidas y evaluar en serio es HU4.

### HU1 — Visión (Hebert) — ✅ Hecho (con limitación conocida en las damas)
- [x] Set de fotos de tablero — en vez de sacar 15-20 propias, se usó el dataset público
      "Chess Pieces" de Roboflow (licencia dominio público, `training/dataset_tablero/`,
      ignorado por git): 289 fotos reales con piezas, distintas posiciones y algo de variación
      de fondo/objetos en cuadro. Supera el mínimo pedido; no reemplaza sacar fotos del
      tablero físico real del proyecto cuando esté disponible.
- [x] Detección de las 64 casillas (transformación de perspectiva + grilla, OpenCV) —
      `backend/servicios/vision/tablero.py`: `detectar_esquinas_tablero` (contorno de 4 lados
      vía Canny + approxPolyDP), `enderezar_tablero` (perspectiva), `dividir_en_casillas`.
      Probado contra 8 fotos reales del dataset (distintas posiciones) sin fallar ninguna; tests
      automatizados con imagen sintética en `backend/servicios/vision/test_tablero.py`.
- [x] Clasificación de pieza por casilla — `training/dataset_piezas.py` genera automáticamente
      recortes de casilla etiquetados (reusa la detección de esquinas + las cajas del dataset de
      Roboflow, proyectando la base de cada pieza a través de la misma transformación de
      perspectiva). `training/entrenar_clasificador_piezas.py` entrena una CNN chica (3 bloques
      conv+batchnorm+pool, PyTorch, entrada 64x64) sobre esos recortes — 13 clases (12 piezas +
      "vacía"). Checkpoint en `training/checkpoints/clasificador_piezas.pt` (ignorado por git —
      hay que correr el script de entrenamiento localmente para generarlo; si hace falta
      compartirlo entre el equipo, por Drive, no por commit).

      Primera versión: 88%/90% accuracy validación/test, pero fallaba sistemáticamente con las
      damas (la clase con menos ejemplos, ~100 de 2869 anotaciones) y confundía caballo con
      torre/alfil. Se corrigió con pesos por clase en la función de pérdida (inversamente
      proporcional a la frecuencia), aumentación de datos (rotación leve + brillo/contraste, para
      no depender tanto de las pocas sesiones de fotos reales del dataset) y más resolución de
      entrada. Resultado: 90% accuracy en test, con **recall por clase mucho más parejo** —
      dama pasó de prácticamente 0% a 73-80%, caballo de confundirse seguido a 81-91%.
      **Limitación conocida que queda:** al compensar tanto el desbalance, ahora a veces confunde
      el *color* de la dama (blanca vs negra) o predice una dama de más donde no hay — sigue
      siendo la pieza menos confiable del clasificador. El resto (peones, torres, alfiles, reyes)
      anda entre 82-100% de recall. Sirve como versión demostrable; seguir mejorando esto
      (más fotos reales propias, no solo el dataset de Roboflow) queda para si sobra tiempo.
- [x] `reconocer_tablero(imagen) -> fen` — `backend/servicios/vision/reconocimiento.py`, junta la detección
      de esquinas + clasificación de piezas y arma el FEN completo. El turno ("w"/"b") se recibe
      como parámetro porque una sola foto no alcanza para saber de quién es — tampoco se puede
      inferir enroque ni al paso, quedan siempre en su valor por defecto ("-").
- [x] Captura desde cámara (RF06) — `backend/servicios/vision/camara.py::capturar_foto_tablero(indice_camara)`,
      vía `cv2.VideoCapture`. Probado contra la cámara real de esta máquina (no solo el caso de
      error), funciona. Todavía no está conectado a un endpoint HTTP ni a una pantalla que
      muestre la foto en vivo — eso es HU6 ("mostrar la imagen capturada"), no esto.
- [x] Detección de la jugada por diff de FEN (RF11) — `backend/servicios/vision/deteccion_movimiento.py::detectar_jugada(fen_antes, fen_despues)`:
      prueba todas las jugadas legales de la posición "antes" y devuelve la que reproduce
      exactamente la ubicación de piezas de "después". No usa nada de IA — es la forma estándar
      de resolver esto, más confiable que tratar de leer la jugada directo de la imagen.

**Definition of Done Sprint 1 — ✅ cumplido:** `calcular_jugada` en verde; `data_pipeline.py`
corrió sobre 200 partidas reales en Colab sin errores, con checkpoint entrenado guardado en
Drive; `reconocer_tablero` reconoce correctamente al menos un tablero de prueba fijo.

---

## Sprint 2 — Interfaz, aprendizaje y configuración

**Objetivo:** visualizar en tiempo real lo que el sistema percibe y decide, primer modelo
entrenado con evaluación real, modo educativo básico, y configuración de partida.

| HU | Descripción | Puntos | Responsable |
|---|---|---|---|
| HU6 | Visualización del Razonamiento en Tiempo Real | 5 | Hebert |
| HU4 | Reentrenamiento y Evaluación del Modelo | 5 | Luis Ángel |
| HU5 | Retroalimentación Técnica de Partidas (antes "Modo Educativo") | 5 | Luis Ángel |
| HU10 | Configuración de Partida | 3 | Luis Ángel |

- [x] HU6 (parcial): imagen capturada visible en pantalla (`GET /vision/foto`), reconocimiento
      de tablero conectado (`POST /vision/reconocer`) y botón "Usar esta posición" para seguir
      jugando digitalmente desde ahí (`POST /partida` con `fen_inicial`) — cierra RF06/RF11 de
      punta a punta en la interfaz, no solo en el backend.
- [x] HU6 (RF21): `analizar_posicion` pide MultiPV y devuelve `variantes_candidatas` (jugada +
      evaluación) junto al resto del análisis, en una sola llamada a Stockfish; Sala de Control
      las muestra en un widget nuevo ("JUGADAS CANDIDATAS"). **Con esto se cierra la versión
      base de HU6** — lo que queda es 🔭 (ampliación de tesis).
- [x] Stockfish instalado localmente sin admin: binario oficial descargado a `tools/stockfish/`
      (ignorado por git), `STOCKFISH_PATH` configurable por variable de entorno — toda la suite
      de tests pasa en esta máquina (antes fallaban 14-15 por no tener el binario).
- El panel de comparación modelo-vs-Stockfish (ver nota de diseño abajo) sigue siendo la
      ampliación de HU6 y queda bloqueado hasta que HU4 dé un modelo conectable.
- [ ] HU4: clasificación de patrones de error + reentrenamiento en lotes versionados +
      evaluación mediante partidas digitales simultáneas. Ver `CLAUDE.md` (regla 1) y
      `PLAN_IMPLEMENTACION_COMPLETO.md` (sección 5): el modelo decide solo, sin depender de
      Stockfish para jugar; la evaluación de Stockfish sí se puede usar como señal de
      entrenamiento (pesar mejor los casos donde coincide con la jugada humana registrada) y
      como métrica para decidir si una versión candidata se promueve (RF15) — eso es lo que
      alimentaría el panel de Razonamiento Neuronal cuando exista `EstrategiaModelo`.
- [ ] HU5: explicación de jugadas y errores frecuentes, principios básicos del ajedrez.
- [x] HU10 (backend): `POST /partida` acepta `tipo_oponente` (RF31) y lo valida al crear la
      partida contra `fabrica_estrategias.TIPOS_SOPORTADOS`, en vez de fallar recién en la
      primera jugada — hoy solo `"motor"` está soportado, pedir otro devuelve 400 explícito.
      `Partida.tipo_oponente` se guarda y `mover()` ya lo usa para elegir la estrategia, en vez
      de tener `"motor"` harcodeado. Queda listo para que `EstrategiaModelo` (HU3/HU4) se sume
      sin tocar `servicio_partida.py` ni las rutas — solo agregar el tipo a la fábrica.
- [ ] HU10 (frontend): selector de tipo de oponente en la pantalla de configuración de partida
      — pendiente en `ProyectGrupal_Taller_SW2_Frontend` (submódulo `frontend/`, repo aparte).
- [ ] HU10: modo educativo — todavía no tiene ni campo ni comportamiento; depende de HU5.

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
Ya existe una versión temprana en `backend/servicios/simulacion/escena.py` (escena de PyBullet con
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

- `backend/modelos/partida.py`, `backend/servicios/partida/servicio_partida.py`,
  `backend/rutas/ruta_partida.py`: partida jugable en memoria por defecto (`crear_partida`,
  `obtener_partida`, `mover`, vía un `RepositorioPartidas` + una `EstrategiaJugada` — ver
  sección 4 de `PLAN_IMPLEMENTACION_COMPLETO.md`), expuesta vía `POST /partida`,
  `GET /partida/{id}`, `POST /partida/{id}/mover`.
- Tablero interactivo en React (`frontend/src/components/Tablero.jsx`).
- **Base de datos (sección 2 y 7):** `backend/database.py` + `backend/modelos/tablas_orm.py`
  (las 4 tablas) + `RepositorioPartidasPostgres`. Si se levanta un Postgres local y se setea
  `DATABASE_URL`, `servicio_partida.py` empieza a persistir ahí solo (sin tocar código); si no,
  sigue igual que antes, en memoria. Probado contra SQLite en memoria (mismas tablas, sin
  tipos específicos de Postgres) — **falta probarlo contra un Postgres real** antes de la
  defensa, por si aparece alguna diferencia de dialecto que SQLite no detecta.

**Pendiente conocido sobre esto:** el humano siempre juega blancas, la promoción de peón
siempre es a dama, y la tabla `jugada` (detalle por movimiento, para RF34/HU4) todavía no la
puebla nadie — hoy solo se persiste el estado de la partida completa. Ninguno bloquea la demo;
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
- **Migración de arquitectura completada** (secciones 3, 4 y 8 de
  `PLAN_IMPLEMENTACION_COMPLETO.md`): el backend pasó de módulos verticales
  (`backend/engine/`, `backend/game/`, `backend/models/`, `backend/simulation/`, `backend/vision/`)
  a capas horizontales en español (`backend/rutas/`, `backend/servicios/`, `backend/esquemas/`,
  `backend/modelos/`, `backend/repositorios/`). De paso se implementaron los 3 patrones de
  diseño acordados: **Strategy** + **Factory Method** (`backend/servicios/estrategias/`, quién
  decide la jugada) y **Repository** (`backend/repositorios/repositorio_partida.py`, reemplaza
  el dict en memoria que vivía suelto en el servicio). Se aprovechó para también resolver un
  acoplamiento raro que había quedado en HU1 (`backend/vision/piezas.py` dependía de
  `training/entrenar_clasificador_piezas.py`, al revés de lo esperable): ahora ambos importan la
  arquitectura de la CNN desde `backend/servicios/vision/modelo_piezas.py`, sin que ninguno
  dependa del otro. Toda la suite de tests corrida después de cada paso, sin regresiones — los
  únicos tests que siguen fallando son los que ya fallaban antes por huecos de esta máquina
  (sin binario de `stockfish`, sin `pybullet` compilable sin Visual Studio).
