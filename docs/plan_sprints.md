# Plan de implementación por sprint

Basado en `PLAN_IMPLEMENTACION_COMPLETO.md` (secciones 13 a 16) y en el Product Backlog de 11
Historias de Usuario (51 puntos totales) definido junto con la documentación de SW2 y Taller
de Grado I. Reemplaza la versión anterior de este archivo, que estaba basada en un borrador
previo del plan (por área, sin las 11 HU balanceadas).

---

## Sprint 1 — Núcleo técnico

**Objetivo:** motor de ajedrez respondiendo jugadas de forma aislada, reconocimiento de
tablero funcionando sobre fotos de prueba, y el pipeline de datos corriendo de punta a punta.

| HU  | Descripción                                         | Puntos | Responsable | Estado   |
| --- | --------------------------------------------------- | ------ | ----------- | -------- |
| HU2 | Motor de Jugadas y Niveles de Dificultad            | 3      | Hebert      | ✅ Hecho |
| HU1 | Reconocimiento de Tablero y Piezas                  | 8      | Hebert      | ✅ Hecho |
| HU3 | Entrenamiento del Modelo con Partidas de Referencia | 5      | Luis Ángel  | ✅ Hecho |

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
- [x] Captura desde cámara (RF06) — `backend/servicios/vision/camara.py::capturar_foto_tablero(fuente)`,
      vía `cv2.VideoCapture`. Configurable por `CAMARA_FUENTE` (índice local o URL de red — celular
      por USB con DroidCam/Iriun, o por WiFi/hotspot con IP Webcam). Conectado a `GET /vision/foto`
      (imagen en vivo en Sala de Control) y a `POST /vision/reconocer` — HU6 cerrada en su versión
      base.
- [x] Detección de la jugada por diff de FEN (RF11) — `backend/servicios/vision/deteccion_movimiento.py::detectar_jugada(fen_antes, fen_despues)`:
      prueba todas las jugadas legales de la posición "antes" y devuelve la que reproduce
      exactamente la ubicación de piezas de "después". No usa nada de IA — es la forma estándar
      de resolver esto, más confiable que tratar de leer la jugada directo de la imagen. Conectada
      a `POST /partida/{id}/mover-desde-foto` (`servicio_partida.mover_desde_foto`) y al botón
      "Detecté un movimiento físico" en Sala de Control — mover una pieza en el tablero real ya
      actualiza la partida digital sin tocar la pantalla, probado en vivo contra la cámara real.

**Definition of Done Sprint 1 — ✅ cumplido:** `calcular_jugada` en verde; `data_pipeline.py`
corrió sobre 200 partidas reales en Colab sin errores, con checkpoint entrenado guardado en
Drive; `reconocer_tablero` reconoce correctamente al menos un tablero de prueba fijo.

---

## Sprint 2 — Onboarding educativo, análisis y configuración

**Objetivo:** flujo completo del jugador desde ingreso hasta aprendizaje: onboarding visual,
diagnóstico de nivel, configuración de partida, análisis en tiempo real durante la partida,
retroalimentación post-partida, estadísticas personales, y reentrenamiento del modelo en lotes.

**Nota de plataforma:** todas las HU de frontend se implementan en **Flutter** (mobile-first),
no React. Flutter permite compilar a iOS/Android/Web desde el mismo código, con mejor
performance en mobile y UX más nativa.

| HU   | Descripción                                 | Puntos | Responsable | Orden      |
| ---- | ------------------------------------------- | ------ | ----------- | ---------- |
| HU12 | Onboarding Educativo Visual                 | 5      | Luis Ángel  | 1️⃣ Primero |
| HU13 | Cuestionario Diagnóstico de Nivel           | 3      | Luis Ángel  | 2️⃣ Segundo |
| HU10 | Configuración de Partida (frontend Flutter) | 3      | Luis Ángel  | 3️⃣ Tercero |
| HU6  | Análisis en Tiempo Real Durante la Partida  | 5      | Hebert      | 4️⃣ Cuarto  |
| HU5  | Retroalimentación Técnica Post-Partida      | 5      | Luis Ángel  | ✅ Hecho   |
| HU14 | Estadísticas Personales y Progreso          | 3      | Luis Ángel  | 5️⃣ Quinto  |
| HU4  | Reentrenamiento y Evaluación del Modelo     | 5      | Luis Ángel  | 6️⃣ Último  |

**Total Sprint 2: 29 puntos.**

### **HU12 — Onboarding Educativo Visual** (5 pts, Luis Ángel)

Flujo de tarjetas interactivas que enseñan las reglas antes de jugar:

- [ ] 8-10 tarjetas (una por pieza + movimientos básicos)
- [ ] Cada tarjeta: imagen, nombre, movimiento, ejemplo interactivo en miniatura
- [ ] Prueba final: pequeño puzzle de 1-2 movimientos para validar comprensión
- [ ] Guardá en sesión: `onboarding_completado = true`

**Salida:** Jugador sabe qué hace cada pieza y cómo se mueve.

### **HU13 — Cuestionario Diagnóstico de Nivel** (3 pts, Luis Ángel)

Evaluación dinámica de nivel antes de la primera partida:

- [ ] 5-8 preguntas (ej: "¿Has jugado ajedrez antes?", "¿Conoces aperturas?", "¿Sabes tácticas?")
- [ ] Backend calcula puntuación → asigna nivel de Stockfish (1-20)
- [ ] Alternativa: si elige "principiante", nivel=5; si "intermedio", nivel=12; si "avanzado", nivel=18
- [ ] Guardá `nivel_diagnosticado` en la sesión del usuario

**Salida:** Cada jugador tiene un nivel personalizado, no random.

### **HU10 — Configuración de Partida (Frontend Flutter)** (3 pts, Luis Ángel)

Pantalla para elegir oponente y parámetros antes de jugar:

- [ ] Selector de oponente: "Motor Stockfish" o "Modelo IA" (grisado si modelo aún no existe)
- [ ] Pre-carga nivel diagnosticado de HU13
- [ ] Opción de cambiar nivel manualmente (slider 1-20)
- [ ] Botón "Jugar" → `POST /partida` con `tipo_oponente` y `nivel`
- [ ] Feedback visual si el backend rechaza el tipo de oponente (400 error)

**Dependencias:** HU13 (nivel pre-cargado).

**Backend:** Ya listo (HU10 backend hecho en Sprint anterior).

**Salida:** Jugador elige contra quién juega.

### **HU6 — Análisis en Tiempo Real Durante la Partida** (5 pts, Hebert)

✅ **Completado.** Retroalimentación visual en vivo mientras el jugador juega:

- [x] **Evaluación actual:** barra de porcentaje ganador (0-100%, no centipawns crudos)
  - Usa fórmula Lichess: `Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)`
- [x] **Indicador de calidad de la jugada:** después de que el jugador mueve, muestra si fue buena/mala
  - Colores y categorías: brillante, mejor, excelente, buena (verde), imprecisión (amarillo), error (naranja), blunder (rojo)
- [x] **Sugerencia de mejor jugada:** muestra la jugada óptima calculada
- [x] **Mate forzado:** si hay mate en N, muestra "MATE en N" en vez de la barra normal
- [x] **Integración con EstrategiaModelo:** el modelo v5 propio (SE-ResNet-8) decide jugadas maestras de forma autónoma con poda táctica.
- [x] **Ampliación (Hebert, esta semana):** el modelo propio ahora se autoidentifica en toda la
      interfaz como **"Turing"** (antes "Caissa" — se cambió porque el avatar 3D es masculino).
      Panel nuevo "Candidatas de Turing" en Razonamiento Neuronal: detalle real de las 3
      candidatas de la red (no solo la elegida), con los 3 chequeos tácticos autónomos que ya
      usa `predecir_jugada_maestra` (jaque mate, mate del rival evitado, pieza colgada) y la
      evaluación de Stockfish de cada candidata puntual (no solo su propia mejor jugada) —
      backend: `explicar_top_candidatas` en `inferencia.py`, sin tocar el comportamiento de la
      jugada real en partidas (verificado con test que compara ambas funciones). Vista alternativa
      del "cerebro" como red de nodos conectados (`CerebroRed.jsx`), seleccionable con un toggle
      junto a la nube de partículas original — mismos datos reales, ambas conviven.
- [x] **Segunda ampliación (Hebert, misma semana):** Razonamiento Neuronal pasó de mostrar
      "todas las partidas del sistema mezcladas, de cualquiera" a un selector de dos pasos
      **elegir estudiante → elegir su partida** (`GET /auth/usuarios` filtrado a rol jugador,
      después `GET /auth/usuarios/{id}/historial-partidas`), con un rótulo fijo "Analizando
      partida de: {nombre}" siempre visible mientras se mira una. Si el estudiante elegido sigue
      jugando (partida no terminada), la pantalla ahora sondea cada 3s y refresca sola el cerebro
      y las candidatas con la jugada nueva — antes era una foto fija de un solo momento. Pantalla
      ahora exclusiva de facilitador (antes la veía cualquier rol sin distinción).
- [x] **Tercera ampliación (Hebert): Turing se adapta al nivel del jugador.** `predecir_jugada_maestra`
      ahora recibe el `nivel` de la partida, que viene del perfil del jugador (Principiante ≈ 5,
      Intermedio ≈ 11, Avanzado ≈ 18). Con nivel >= 18 se comporta igual que antes; por debajo muestrea
      con softmax entre sus 3-5 mejores candidatas (`temperatura_y_pool_por_nivel`), sin dejar de jugar
      el mate en 1 ni de evitar jugadas que permiten mate en 1. Sigue decidiendo solo con su red (sin
      Stockfish) y sin aprendizaje en vivo; `explicar_top_candidatas` no se tocó.

**Salida:** Jugador ve feedback visual EN TIEMPO REAL, diferenciador vs ChessKid/Chess.com.

### **HU5 — Retroalimentación Técnica Post-Partida** (5 pts, Luis Ángel)

✅ **Completado.** Vista "Aprendizaje" y Tutoría Pedagógica:

- [x] Lista de jugadas clasificadas con explicación del principio ajedrecístico violado o aplicado (qué/por qué/cómo)
- [x] Curva de efectividad (Win% turno a turno a lo largo de la partida)
- [x] Resumen post-partida: precisión global ponderada, conteo de calidades y consejo pedagógico del tutor virtual
- [x] Panel de detalle de cada jugada con FEN antes/después y sugerencia de alternativa óptima

**Salida:** Jugador entiende qué salió mal y cómo mejorar de manera amena y educativa.

**Ampliación (Hebert, esta semana) — cierra el hueco real de RF20.** Revisando el documento
oficial del Taller de Grado se confirmó que el criterio de aprobación de HU5 en ese documento es
literalmente *"Modo Educativo"* con RF20 — *"transmitir principios básicos del ajedrez adaptados
al nivel de cada participante"* — y que, pese a que esta sección ya decía "Completado", el código
real (`explicar_jugada`/`generar_resumen_partida`) generaba el mismo texto sin importar el nivel
del jugador. Se avisó a Luis Ángel antes de tocar su HU y se avanzó igual dado que es un hueco
central para la defensa (falta de "alguien que le enseñe" es la situación problemática del propio
documento). Implementado:

- [x] `explicar_jugada`/`generar_resumen_partida` ahora reciben `rango` (`Principiante`/
      `Intermedio`/`Avanzado`, mismos valores que `UsuarioORM.rango_estimado`) y devuelven texto
      distinto por cada una de las categorías de principio ajedrecístico — Intermedio es el texto
      que ya existía (sin regresión), Principiante simplifica sin jerga y con tono que anima,
      Avanzado agrega el dato numérico (pérdida en peones) y vocabulario técnico preciso.
- [x] `GET /partida/{id}/analisis-completo` adapta la respuesta al `rango_estimado` real del
      usuario autenticado (`Intermedio` si no hay token o el jugador no se diagnosticó todavía —
      el endpoint sigue funcionando sin login, no se le exigió auth nueva para no romper el uso
      existente).
- [x] **Bug real encontrado y corregido de paso:** el análisis retrospectivo usaba el mismo
      `Skill Level` débil configurado para la partida también para evaluar objetivamente las
      jugadas ya jugadas — en niveles bajos Stockfish daba evaluaciones sin sentido (le decía al
      jugador "te perdiste de capturar la dama" justo después de capturarla). Ahora el análisis
      retrospectivo siempre corre a fuerza máxima, sin importar el nivel de la partida.

### **HU14 — Estadísticas Personales y Progreso** (3 pts, Luis Ángel)

Dashboard post-partida con métricas personales:

- [ ] Partidas jugadas (total, por oponente)
- [ ] Promedio de efectividad (Win% promedio de todas sus partidas)
- [ ] Errores más frecuentes (si tiene 3+ partidas, muestra top 3 categorías)
- [ ] Racha de victoria actual
- [ ] Meta visual: "Mejoraste un 2% respecto a ayer" (si aplica)
- [ ] Gráfico de progreso semanal (línea simple)

**Dependencias:** HU5 (necesita datos de análisis).

**Salida:** Jugador ve su progreso real, gamificación que lo motiva a jugar más.

### **HU4 — Reentrenamiento y Evaluación del Modelo** (5 pts, Luis Ángel)

Ciclo de mejora automática del modelo propio:

- [ ] **Recopilación:** después de N partidas contra el modelo (ej. 10), recopila historial
- [ ] **Análisis:** llama `GET /partida/{id}/analisis-completo` para cada partida
- [ ] **Clasificación de errores:** identifica en qué tipo de posiciones falla el modelo
- [ ] **Reentrenamiento:** sube los datos a Colab, reentrenamiento con HU3 base + datos nuevos
- [ ] **Versionado:** guarda checkpoint como `modelo_jugadas_v2_2026-09-17.pt` en Google Drive
- [ ] **Evaluación:** juega 10-20 partidas modelo-vs-Stockfish, calcula:
  - Tasa de victoria del modelo
  - ACPL promedio (centipawn loss del modelo)
  - Coincidencia con Stockfish (%)
- [ ] **Promoción:** si métricas mejoran → promueve versión; si no → rollback

**Nota importante (regla 1 de `CLAUDE.md`):** El modelo decide **solo**, sin depender de
Stockfish para jugar. Stockfish es **solo para medir** — comparación paralela, no en el camino
de decisión.

**Salida:** El modelo se reentrenó y está más fuerte. Diferenciador clave: motor que aprende
de usuarios.

**Avance de base para HU4 (Sala de Control, ver `backend/servicios/partida/ciclo_vida.py`):**
la Sala de Control creaba una partida apenas se abría la pantalla, sin botón "iniciar", y nunca
cerraba la anterior — de 399 partidas reales, 347 no tenían ni una jugada del jugador. Ahora
cada partida tiene un `estado` (`en_curso`/`terminada`/`abandonada`), las pendientes se cierran
solas (al crear una nueva del mismo usuario, y con un barrido periódico por inactividad), y el
Registro/historial excluyen las que nunca se jugaron. Sobre esa base, el facilitador tiene un
panel (`GET /entrenamiento/estado`, `POST /entrenamiento/dataset`) para descargar como ZIP
(PGN + CSV, anónimo) las partidas "válidas" (terminadas, ≥5 jugadas del jugador, dueño jugador)
y ver cuándo hay "suficientes" nuevas — el reentrenamiento en sí (los pasos de arriba) sigue
sin construirse; esto solo junta la materia prima.

---

### **Flujo del Jugador Completo (Ahora)**

```
1. Abre la app (Flutter mobile)
   ↓
2. VE ONBOARDING (HU12) — "Aprende qué es cada pieza" (tarjetas interactivas)
   ↓
3. HACE CUESTIONARIO (HU13) — "¿Cuál es tu nivel?" (5 preguntas)
   ↓
4. CONFIGURA PARTIDA (HU10) — "Contra quién querés jugar? Motor o Modelo?" (selector)
   ↓
5. JUEGA Y VE ANÁLISIS EN VIVO (HU6) — "¿Estoy jugando bien?" (barra Win%, indicador calidad)
   ↓
6. TERMINA Y VE ANÁLISIS DETALLADO (HU5) — "Qué salió mal y por qué" (lista + curva)
   ↓
7. VE SU PROGRESO (HU14) — "Mejoraba un 2% hoy, mi racha es 3 victorias" (dashboard)
   ↓
8. [BACKGROUND] MODELO SE REENTRENÓ (HU4) — "Próxima versión lista" (después de 10 partidas)
   ↓
9. JUEGA DE NUEVO, Y EL MODELO ESTÁ MÁS FUERTE
```

---

### **Cambios vs Sprint 2 Original**

| Aspecto                 | Antes                            | Ahora                                                                    |
| ----------------------- | -------------------------------- | ------------------------------------------------------------------------ |
| **HU en Sprint 2**      | 4 (HU6, HU4, HU5, HU10)          | 7 (HU12-14 nuevas)                                                       |
| **Puntos totales**      | 18                               | 29 (más realista)                                                        |
| **Plataforma frontend** | React (web)                      | **Flutter (mobile-first)**                                               |
| **Flujo del jugador**   | Desorganizado, sin onboarding    | Completo de punta a punta                                                |
| **HU6 bloqueador**      | Bloqueada por HU4                | Desacoplada, se hace independiente                                       |
| **Diferenciadores**     | Solo análisis post-partida       | + Onboarding + Diagnóstico + Análisis en tiempo real + Progreso personal |
| **Competencia**         | Vs Chess.com/Lichess (genéricos) | Vs ChessKid (pero mejor UX)                                              |

---

### **Dependencias y Orden de Ejecución**

```
HU12 (Onboarding)
  ↓
HU13 (Diagnóstico) — independiente, pero depende de HU12 terminada
  ↓
HU10 (Config) — depende de HU13 (nivel pre-cargado)
  ↓
HU6 (Análisis en vivo) — independiente, Hebert puede empezar en paralelo
  ↓
HU5 (Análisis post-partida) — ✅ ya hecho
  ↓
HU14 (Estadísticas) — depende de HU5
  ↓
HU4 (Reentrenamiento) — depende de HU5 (usa `analisis-completo`)
```

**Puede haber paralelismo:** Hebert en HU6 mientras Luis Ángel hace HU12-13-10.

---

## Sprint 3 — Brazo robótico y cierre

**Objetivo:** interconexión con el brazo (simulado), rostro y expresiones, panel de
progreso, administración de sesiones, e integración completa para la defensa.

| HU   | Descripción                                | Puntos | Responsable |
| ---- | ------------------------------------------ | ------ | ----------- |
| HU9  | Interconexión con el Brazo Robótico        | 8      | Hebert      |
| HU7  | Rostro y Expresiones del Sistema           | 3      | Luis Ángel  |
| HU8  | Panel de Progreso                          | 3      | Luis Ángel  |
| HU11 | Administración de Sesiones y Participantes | 3      | Luis Ángel  |

### Sobre el simulador — avance real (adelantado, HU9 parcial)

Ya no es solo la versión temprana con casillas vacías. `backend/servicios/simulacion/escena.py`
ahora arma la posición inicial completa con las 32 piezas reales (modelos 3D generados con IA,
estilo Staunton, optimizados de cientos de miles de caras a ~2500 cada una y de decenas de MB a
unos pocos cientos de KB — assets en `backend/servicios/simulacion/assets/piezas/{claro,oscuro}/`),
ubicadas vía `python-chess` (sin hardcodear casillas), con escala y orientación calibradas
(`ESCALA_PIEZA`, corrección de eje Y-arriba→Z-arriba verificada contra los `.obj` crudos, no
asumida). `sincronizar_piezas` permite reflejar cualquier posición arbitraria, no solo la inicial.

**Puente 2D↔3D ya funcionando:** `backend/servicios/simulacion/ver_partida_en_vivo.py` abre una
ventana nativa de PyBullet que sondea `GET /partida/{id}` cada 1s y actualiza las piezas en vivo
mientras se juega en la web — sin tocar nada manualmente. Se puede lanzar a mano
(`ver_simulacion_3d.bat <partida_id> <token>` en la raíz del repo) o con un clic desde Sala de
Control (botón "Abrir simulación 3D", `POST /simulacion/abrir-ventana-3d`, el backend lanza el
proceso). Entorno conda `ajedrez` (con PyBullet real) ya armado y probado en la máquina de Hebert
— `environment.yml`/`requirements.txt` tenían pines de versión inexistentes
(`pybullet=3.25` en conda-forge sí existe — verificado con `conda search`, era `python-chess`
el nombre de paquete viejo/incorrecto, ya corregido a `chess==1.11.2`, la distribución PyPI real).

**Cambio de alcance real, no de ESP32 genérico:** la universidad (FICCT) ya trajo el kit real —
no es un ESP32+PCA9685 armado a medida, es un **DOBOT CR5AS** (robot colaborativo de 6 ejes,
5kg de carga, 900mm de radio, con visión artificial disponible para pick-and-place — ficha técnica
de DIDACTECH SRL revisada). Tiene protocolo TCP/IP oficial documentado (puertos 29999
comandos/30004 feedback, SDK Python oficial `Dobot-Arm/TCP-IP-Python-V4`) — mucho más viable que
armar un controlador propio desde cero. Software de configuración inicial: DobotStudio Pro
(activar modo TCP/IP una sola vez, no es lo que habla nuestro backend en tiempo real).
Conexión real programada para probar en la universidad — pendiente confirmar en persona.

**Todavía sin empezar (el núcleo real de HU9):**
- [ ] `EjecutorReal` (interfaz `ejecutar_movimiento(origen, destino, captura)`, mismo patrón
      Strategy que `EjecutorSimulado`) que hable con el Dobot real por TCP/IP — no escrito
      todavía, ni siquiera un esqueleto; recién se investigó el protocolo, no se implementó.
- [ ] Cinemática inversa real (coordenadas de casilla del tablero físico → posición XYZ del
      brazo) — depende de calibrar el tablero físico real contra el espacio de trabajo del Dobot,
      todavía no hecho.
- [ ] **Visión para guiar el brazo real (distinto de HU1):** HU1 ya reconoce el tablero desde una
      foto para actualizar el estado digital de la partida — eso está resuelto desde Sprint 1. Lo
      que falta es un problema distinto: que el Dobot ubique con precisión una pieza física
      específica para agarrarla (pick-and-place guiado por cámara), que es lo que dilucida el PDF
      de DIDACTECH (visión 2D/3D + calibración cámara-robot + herramienta final) — nada de esto
      arrancó, es trabajo nuevo de HU9, no una extensión de HU1.
- [ ] Integración de punta a punta con al menos 10 posiciones de prueba documentadas.
- [ ] Colchón de 2-3 días antes de la defensa para bugs de integración.

- [ ] HU7, HU8, HU11: interfaz y lógica de cada una — sin empezar (Luis Ángel).

---

## Dashboard por rol y Módulo de Enseñanza (Hebert, adelantado fuera de HU puntuales)

Punto de partida: releer el documento oficial del Taller de Grado (`situación problemática` /
`situación deseada`, sección 3-4) dejó claro que "falta alguien que enseñe" es literalmente el
problema central a demostrar en la defensa — esto llevó a cerrar RF20 (arriba, en HU5) y a
construir toda la plataforma de roles que hacía falta para que tuviera sentido. Nada de esto
rompe HU1/HU2/HU3/HU9, que siguen intactas.

**División real por rol (antes, `jugador` y `facilitador` veían las mismas pantallas sin
distinción):**

- [x] **Sala de Control**, **Razonamiento Neuronal**, **Monitoreo** y **Configuración de
      Enseñanza**: ahora exclusivas de facilitador (antes accesibles a cualquier rol logueado).
- [x] **Panel de Aprendizaje**: pantalla nueva, exclusiva de jugador — es la que responde RF20 en
      la interfaz: nivel + ruta de progreso, repaso de la última jugada relevante (adaptado por
      nivel, con glosario de términos tocable), galería de las 6 piezas con mini-tablero de
      movimientos legales ilustrativo, resumen del tutor, logros básicos (datos reales, no
      simulados), sección "Próximamente" (multijugador/ranking — visión de tesis, no de este
      sprint) y narración por voz real con la Web Speech API del navegador (sin dependencia
      nueva).
- [x] **Mi Perfil**: nuevo, cualquier rol — nombre/foto/edad/bio editable (`PATCH /auth/me`).
- [x] **Permisos por partida**, controlados por el facilitador, apagados por defecto: simulación
      3D y cámara del tablero físico quedan ocultas al jugador hasta que el facilitador las
      activa puntualmente para esa partida (`PATCH /partida/{id}/permisos`) — el E-STOP del brazo
      NO tiene este toggle, queda hardcodeado solo-facilitador por ser control de seguridad.
- [x] **Modo demostración en vivo**: el facilitador puede jugar una partida propia para mostrarle
      a la clase cómo jugar y "transmitirla" — cualquier jugador la ve en solo lectura sin que se
      comparta nada a mano (`GET /partida/demostracion-activa`, banner + pantalla dedicada del
      lado del jugador).
- [x] **Monitoreo**: pantalla tipo DVR de cámaras para el facilitador — hasta 4 tableros de
      estudiantes EN CURSO a la vez (agrupado por jugador, no por partida — una sola tarjeta por
      estudiante aunque tenga partidas viejas sin terminar), clic en uno lo agranda, paginación si
      hay más de 4, badge del nivel diagnosticado de cada estudiante.
- [x] **Configuración de Enseñanza**: panel del facilitador para subir un video corto por pieza
      (`POST /facilitador/videos/{tipo_pieza}`, sirve por `/media/videos_piezas/...`) y elegir un
      preset de tono (Infantil/Estándar/Adultos, `preset_ensenanza` en el perfil) — documentado
      explícitamente en la interfaz que este preset **todavía no se aplica a estudiantes reales**
      porque no existe una tabla de curso/grupo que vincule facilitador↔estudiantes (queda anotado
      como hueco real, no resuelto ni escondido).
- [x] **Interfaces "en vivo" de verdad, no fotos fijas**: cualquier pantalla donde el facilitador
      mira algo que otra persona puede estar cambiando en ese momento sondea el backend — Sala de
      Control al ver la partida de un estudiante (2.5s, además el tablero queda de solo lectura,
      el facilitador no puede intervenir en la partida de nadie), Razonamiento Neuronal al analizar
      una partida en curso (3s), Monitoreo (5s la lista, 1.5s el tablero agrandado), Demostración
      en vivo (1.5s).
- [x] **Bug real encontrado y corregido:** `RepositorioPartidasPostgres` reconstruía el tablero
      siempre desde la posición inicial estándar, ignorando `fen_inicial` — cualquier partida
      arrancada desde una posición armada en el tablero físico (HU1) perdía esa posición al
      releerla de la base. Corregido; filas viejas sin esa columna siguen usando la posición
      estándar (no se rompe nada retroactivo).
- [x] **Calibración de nivel por partida (RF20 ampliado):** cada partida terminada del jugador
      calibra su nivel (`POST /partida/{id}/calibrar`, y también al abrir `analisis-completo`). Se
      comparan contra Stockfish solo las jugadas del propio jugador (`precision_jugador`, no las de
      ambos bandos) y queda una fila por partida en `calibracion`, única por usuario+partida: re-analizar
      no duplica ni revierte el nivel. El nivel vigente es el promedio de las últimas 3 calibraciones y
      una partida con menos de 5 jugadas del jugador no cuenta. `GET /auth/nivel` devuelve nivel,
      progreso al siguiente nivel, historial y escala (0-20; Turing con techo en 18 "Maestro",
      Stockfish usa 0-20 completo). El modelo propio no interviene en el cálculo del nivel; la primera
      partida contra Stockfish como diagnóstico la impone el frontend, no el servidor.

**Todavía sin empezar / explícitamente fuera de alcance de este sprint:** vínculo real
facilitador↔curso↔estudiantes (bloquea que el preset de enseñanza y el selector de "grupo" de
Monitoreo/Configuración de Enseñanza hagan algo más que mostrar un placeholder "Próximamente");
multijugador, matchmaking por nivel y ranking (Módulo 7 del documento oficial, "visión de tesis"
explícita, no de este sprint); tutor conversacional real (LLM con tools/system-prompt/multi-turn)
— evaluado y descartado para este sprint por tiempo/alcance, el nivel-adaptativo actual (RF20) se
resuelve con plantillas escritas a mano, no con un modelo de lenguaje.

**Pendiente para Sprint 2 (mismo hueco de arriba, encontrado al revisar por qué el jugador nunca
ve el video de su facilitador):** el jugador sube su video por pieza en Configuración de
Enseñanza, pero en "Aprendé cada pieza" (Panel de Aprendizaje) el jugador siempre ve un
placeholder fijo que dice "Próximamente" — ni siquiera intenta pedir el video, no es un bug de
conexión suelto. Dos motivos, los dos ya reales hoy: (1) `GET /facilitador/videos` exige rol
facilitador (`get_current_facilitador`), así que un jugador no tiene por dónde pedirlo aunque el
frontend lo intentara; (2) no hay tabla de curso/grupo (el hueco de arriba), así que tampoco está
definido de qué facilitador debería ver el video un jugador dado. Resolverlo bien depende de
cerrar primero el vínculo facilitador↔curso↔estudiantes, no es solo conectar un fetch.

**Pendiente transversal (todo el frontend, no una pantalla puntual): que el sistema sea
responsive de verdad en cualquier tamaño de pantalla, no solo escritorio.** Hoy es parejo: cada
pantalla nueva usó los breakpoints de Tailwind (`sm:`/`md:`/`lg:`) por su cuenta, sin una revisión
conjunta en dispositivos chicos. Medido por cantidad de esos breakpoints por archivo
(`frontend/src/paginas/*/*.jsx`): pantallas como Panel de Aprendizaje, Registro de Partidas o
Razonamiento Neuronal tienen bastantes; **Sala de Control — la pantalla principal de juego — tiene
pocos para lo compleja que es (tablero + 3 columnas)**, y los componentes más nuevos
(`ModalRetomarPartida.jsx`, `ChatTuring.jsx`, `CerebroNeuronal.jsx`/`CerebroRed.jsx` con el canvas
3D) no tienen ninguno todavía. Falta una pasada dedicada, pantalla por pantalla, en anchos de
celular y tablet, no solo confiar en que cada una haya heredado clases responsive de una vecina.

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
