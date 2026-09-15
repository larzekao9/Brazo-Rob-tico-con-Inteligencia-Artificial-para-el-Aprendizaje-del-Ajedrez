# Plan de Implementación Completo — Plataforma de Ajedrez Potenciada por Inteligencia Artificial

Equipo: Suárez Burgos Hebert · Arze Kao Luis Ángel

> **Principio rector: hay un solo software.** Este plan sirve para programar, sin importar
> si documentan primero para SW2 o para Taller de Grado I — el código, la base de datos y
> el orden de trabajo son los mismos. Lo único que cambia entre materias es el formato del
> documento que llenan *después* de programar, nunca el software en sí.

---

## 0. Dos horizontes de alcance — no confundir uno con otro

Este documento mezcla dos cosas a propósito, porque es un solo software con dos fechas de
entrega distintas encima. Para no perderse, cada RF y cada caso de uso de las secciones 10 y
11 lleva una marca:

- **🟢 Sprint actual (defensa SW2, 1-2 semanas):** las 11 HU del Product Backlog (sección 13),
  51 puntos. Es lo único que hay que tener funcionando para la defensa inminente.
- **🔭 Visión de tesis (Taller de Grado I y en adelante):** todo lo que agrega este documento
  más allá de las 11 HU — login de jugadores (JWT), plataforma multiusuario online, panel de
  administrador con promoción de versiones de modelo, mapa de atención (Grad-CAM) en vivo por
  WebSocket, cinemática inversa real del brazo. Es la arquitectura a la que el software
  converge con el tiempo, **no algo a programar antes de la defensa de SW2.**

Si alguna vez este documento y el sprint actual (`docs/plan_sprints.md`) parecen contradecirse
en qué hay que hacer *ya*, gana `docs/plan_sprints.md` — es el tablero de seguimiento del
sprint real, este documento es la arquitectura y el backlog completo del proyecto.

---

## 1. Objetivo General y Alcance

**Nombre del proyecto: "Plataforma de Ajedrez Potenciada por Inteligencia Artificial".**

Desarrollar una plataforma de ajedrez con inteligencia artificial que combine un motor de
cálculo consolidado (Stockfish) con un modelo de aprendizaje propio entrenado sobre partidas
humanas, capaz de jugar y explicar jugadas al estilo humano, retroalimentarse en lotes
controlados a partir de las partidas jugadas en línea, y ejecutar físicamente las jugadas
mediante un brazo robótico simulado y, a futuro, real. El software es el cerebro (percepción,
decisión, aprendizaje, explicación); el brazo robótico es el cuerpo — un anexo de ejecución
física y de valor demostrativo, no el centro del proyecto.

### Dónde concentrar el esfuerzo

El componente central de este proyecto es el sistema de inteligencia artificial (HU3, HU4,
HU5): el motor que aprende de partidas humanas, se retroalimenta con datos propios, y actúa
como entrenador dando feedback técnico. Es ahí donde debe concentrarse la mayor profundidad de
documentación, pruebas y pulido. El brazo robótico (HU9) es una interacción física
complementaria — debe funcionar y verse bien en la demo, pero no debe consumir tiempo de
desarrollo a costa del núcleo de IA. No hace falta cinemática perfecta ni un brazo elegante:
alcanza con que ejecute la jugada de forma confiable.

### Objetivos específicos

- Diseñar la arquitectura del sistema en capas (patrón MVC), separando percepción, decisión,
  aprendizaje, ejecución y presentación.
- Construir el módulo de reconocimiento de tablero y piezas mediante visión por computadora.
- Integrar el motor Stockfish como uno de los oponentes disponibles (configurable por niveles
  de dificultad) y como oráculo de comparación para medir qué tan entrenado está el modelo
  propio — no como validador del que el modelo dependa para decidir.
- Entrenar un modelo de aprendizaje automático que decida, prediga y explique jugadas al estilo
  humano por su cuenta, por bandas de nivel/estilo, sin depender de Stockfish para razonar.
- Reentrenar el modelo en lotes controlados y versionados, usando partidas de referencia
  (Lichess) y partidas jugadas en línea.
- Desarrollar un módulo de visualización que muestre, en tiempo real, el razonamiento del
  modelo (mapa de atención, confianza, entropía) junto al análisis de Stockfish. **🔭**
- Resolver la cinemática del brazo (directa e inversa) para traducir cada jugada calculada en
  una secuencia física ejecutable, primero en simulador (PyBullet) y luego en hardware real. **🔭**
- Ofrecer una plataforma web donde cualquier jugador pueda jugar en línea contra el motor o el
  modelo, y donde un administrador pueda gestionar modelos, sesiones y configuración del
  sistema. **🔭**
- Habilitar un entorno de práctica y competencia entre jugadores humanos (emparejamiento por
  nivel, torneos, ranking) que dé continuidad a la formación más allá de jugar contra la IA. **🔭**
- Validar el sistema con pruebas piloto documentadas.

### Alcance

**Dentro de alcance (del proyecto completo, no solo del sprint actual):** plataforma web de
ajedrez online contra motor/modelo; pipeline de entrenamiento y reentrenamiento en lotes;
panel de administración del modelo (entrenar, evaluar, versionar, promover); módulo de visión
sobre tablero físico; módulo de visualización del razonamiento (mapa de atención, confianza);
brazo robótico en simulador reflejando las jugadas; seguimiento de progreso del jugador;
administración de sesiones y participantes para el contexto del curso. **🔭 Ampliación de
visión (post-defensa SW2):** perfil y registro del jugador con historial; evaluación inicial de
nivel para jugadores nuevos; emparejamiento (matchmaking) entre jugadores humanos por nivel
similar; sistema de ranking; gestión de torneos, categorías y resultados; panel de la
organización deportiva (Asociación) para publicar eventos y hacer seguimiento de participación.

**Fuera de alcance (en cualquier horizonte, por ahora):** aprendizaje en vivo durante una
partida en curso; ejecución sobre el brazo físico real (depende de la llegada del kit); modelo
personalizado por oponente individual (se usa el enfoque por bandas de nivel/estilo, tipo
Maia, no un modelo 1-a-1 por jugador).

---

## 2. Antes de escribir código: qué deciden juntos, una sola vez

Esto se hace en una sola sesión de 1-2 horas, los dos juntos, antes de que cada uno arranque
por su lado. Si no lo hacen, van a terminar con formatos de datos incompatibles entre el
módulo de Hebert y el de Luis Ángel.

- [x] Crear el repositorio en GitHub (uno solo, no uno por persona).
- [x] Acordar el **contrato de datos entre módulos**: ¿en qué formato exacto se pasan un
      tablero entre el módulo de visión y el módulo de motor? Recomendación: **FEN**
      (Forsyth-Edwards Notation), el estándar de ajedrez — es una sola línea de texto,
      ejemplo: `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`. Todo el proyecto
      habla en FEN entre sí; nadie inventa su propio formato de tablero.
- [x] Crear el archivo `requirements.txt` vacío y decidir juntos cada versión a medida que
      la agreguen (no dejar ninguna dependencia "sin fijar").
- [ ] Crear las 4 tablas mínimas de la base de datos (sección 7) — esto lo hace una sola
      persona, no las dos por separado, para evitar migraciones en conflicto.

---

## 3. Arquitectura de Software — Patrón MVC (organizado en capas)

Se adopta MVC (Modelo-Vista-Controlador) en su forma orientada a servicios, apropiada para un
backend que expone una API y no arma HTML directamente — el frontend (React) es la Vista, y el
"Controlador" se separa en dos capas explícitas (Rutas y Servicios) para mantener la lógica de
negocio aislada de la capa HTTP.

| Capa MVC | Sub-capa | Responsabilidad | Carpeta |
|---|---|---|---|
| Controlador | Rutas | Recibe la petición HTTP/WebSocket, valida entrada, llama al servicio correspondiente | `backend/rutas/` |
| Controlador | Servicios | Lógica real de negocio: percepción, decisión, aprendizaje, ejecución | `backend/servicios/` |
| Modelo | Esquemas | Forma exacta de los datos que entran y salen de cada endpoint (Pydantic) | `backend/esquemas/` |
| Modelo | Modelos de datos | Representan las tablas de la base de datos | `backend/modelos/` |
| Vista | Frontend (React) | Lo que ve y usa el jugador o el administrador | `frontend/` |

Cada caso de uso nuevo se construye siempre de adentro hacia afuera: modelo de datos (si hace
falta) → servicio → ruta → pantalla del frontend que la consume.

### Por qué esta arquitectura y no otra

- Separa "qué pide el usuario" (rutas) de "qué hace el sistema" (servicios): si mañana cambian
  de cámara o prueban otro motor de ajedrez, tocan un solo archivo de servicio, no todo el
  sistema.
- Encaja directo con lo que pide la materia de SW2: el "Diagrama de Paquetes organizado en
  capas" que exige el Capítulo 3 es literalmente este esquema, dibujado.
- No es sobre-ingeniería: para 2 personas y unas semanas, microservicios o arquitecturas más
  complejas solo agregarían trabajo sin necesidad real.

**Estado actual del código vs. este esquema:** migrado. El backend ya está organizado en estas
capas horizontales (`backend/rutas/`, `backend/servicios/`, `backend/esquemas/`,
`backend/modelos/`) — ver sección 8 (Estructura del repositorio) para el árbol completo.

---

## 4. Patrones de Diseño Aplicados

### 4.1 Strategy

Se usa donde el sistema debe poder intercambiar una implementación por otra sin que el resto
del código lo note, definiendo una interfaz común y varias implementaciones concretas:

- **Selección de oponente 🟢 — implementado.** `backend/servicios/estrategias/estrategia_jugada.py`:
  interfaz `EstrategiaJugada` (`decidir_jugada(fen)`) con `EstrategiaStockfish` ya funcionando.
  `EstrategiaModelo` (cuando HU3/HU4 den un modelo entrenado) y `EstrategiaHumano` quedan como
  extensión futura de la misma interfaz — el jugador elige la estrategia activa por partida
  (`tipo_oponente`, contemplado en la tabla `sesion` de la sección 7, aunque HU10 todavía no
  conecta esa elección a la API). **Importante:** `EstrategiaModelo.decidir_jugada` va a razonar
  únicamente con la red entrenada propia — no va a llamar a `EstrategiaStockfish` internamente
  para decidir ni para validar. La comparación contra Stockfish (ver regla 1 de `CLAUDE.md`) es
  un cálculo aparte, en paralelo, para medir al modelo — no una dependencia de su camino de
  decisión.
- **Ejecutor de movimientos del brazo 🔭** — interfaz `ejecutar_movimiento(origen, destino,
  captura)`, con una implementación `EjecutorSimulado` (PyBullet, la que ya existe en
  `backend/servicios/simulacion/escena.py`) y una `EjecutorReal` (ESP32 + PCA9685) a futuro.
  Permite desarrollar y probar todo el sistema sin depender de que el hardware físico esté
  listo, y cambiar a producción real sin tocar el resto del backend. Todavía no está escrita
  como interfaz formal (alcance de tesis, no de este sprint).

### 4.2 Factory Method

Complemento natural de Strategy — sin esto, el `if/elif` de qué estrategia usar termina
desparramado por el código en vez de en un solo lugar:

- **Implementado.** `backend/servicios/estrategias/fabrica_estrategias.py::crear_estrategia_jugada(tipo_oponente, nivel)`
  decide qué implementación de la 4.1 instanciar. Hoy solo soporta `"motor"` — pedir cualquier
  otro tipo lanza `ValueError` explícito, en vez de fallar en silencio.

### 4.3 Repository

Se usa para desacoplar el acceso a datos de la lógica de servicios, de modo que los servicios
no dependan directamente de SQLAlchemy ni de la estructura exacta de las tablas:

- **`RepositorioPartida` implementado** — `backend/repositorios/repositorio_partida.py`:
  interfaz `RepositorioPartidas` (`guardar`, `obtener`) con `RepositorioPartidasEnMemoria` como
  única implementación por ahora (el mismo dict que antes vivía suelto en el servicio, ahora
  detrás de la interfaz). `RepositorioPartidasPostgres` se agrega recién cuando llegue HU11 con
  la base de datos real — no hace falta instalar Postgres para tener el patrón funcionando hoy.
- `RepositorioJugada` — 🔭 todavía no existe (no hay entidad `Jugada` persistida, ver sección 7).
- También facilita los tests unitarios: `backend/repositorios/test_repositorio_partida.py`
  prueba el repositorio en memoria sin ninguna base de datos corriendo.

### 4.4 Ya presentes en el código, sin haber sido nombrados (gratis para la documentación)

- **Facade** — `backend/servicios/vision/reconocimiento.py::reconocer_tablero(imagen) -> fen`
  esconde 4 pasos (esquinas, perspectiva, clasificación, armado de FEN) detrás de una sola
  llamada. Mismo caso con `calcular_jugada(fen, nivel)` tapando toda la comunicación UCI con
  Stockfish.
- **Adapter** — `backend/servicios/motor/motor_ajedrez.py` adapta la interfaz genérica de
  `chess.engine` a la interfaz específica que necesita el proyecto.
- **Singleton (a nivel de módulo)** — `backend/servicios/vision/piezas.py` carga el modelo de
  PyTorch una sola vez (`_modelo`, `_clases` a nivel de módulo) y lo reusa en cada
  clasificación, en vez de recargarlo en cada llamada.

---

## 5. Roles

- **Jugador** — cualquier persona que juega en línea contra el motor o el modelo. **🔭** La
  versión con cuenta/login (JWT) es alcance de tesis; hoy cualquiera que abre la página juega,
  sin autenticación.
- **Administrador** — gestiona el modelo de IA (entrena, evalúa, promueve versiones), configura
  el comportamiento del sistema, y administra sesiones y participantes cuando el sistema se usa
  en el contexto del curso con la Asociación Departamental de Ajedrez. **🔭** No existe todavía
  ningún panel ni rol diferenciado — es HU10/HU11 en su versión mínima, y el panel completo de
  promoción de modelos es alcance de tesis.
- **Motor/Modelo de IA** (actor no humano) — restringido por reglas de negocio fijas: cada
  oponente decide sus propias jugadas de forma independiente (Stockfish cuando `tipo_oponente =
  "motor"`, el modelo propio cuando `tipo_oponente = "modelo"`, sin que uno dependa del otro para
  razonar); Stockfish se usa además como oráculo de comparación para medir al modelo, nunca como
  su validador; el modelo propio nunca aprende en vivo durante una partida (ver `CLAUDE.md`,
  reglas técnicas obligatorias). **🟢** Ya vigente.

  La independencia es en tiempo de inferencia (el modelo jugando una partida), no en el proceso
  de entrenamiento: durante HU4, usar la evaluación de Stockfish como señal adicional para pesar
  mejor los casos de entrenamiento (ej. preferir los casos donde la jugada humana registrada
  coincide con lo que Stockfish también favorecía) es una técnica válida y no rompe esta regla.

---

## 6. Stack Tecnológico Completo

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Ya decidido — rápido de escribir, documentación automática (Swagger/OpenAPI), tipado con Pydantic |
| Frontend | React (con Vite) | Mismo stack que usan los proyectos de referencia de la materia; permite actualización en vivo para HU6 |
| Tiempo real | WebSockets (FastAPI ya los trae) | Necesario para HU6 y para el mapa de atención en vivo (🔭) — mostrar jugada y análisis sin recargar la página |
| Autenticación 🔭 | JWT | Para login de jugadores/administrador — alcance de tesis, no del sprint actual |
| Base de datos | PostgreSQL | El equipo ya tiene experiencia con él (proyecto anterior de semáforos) |
| Visión por computadora | OpenCV | Ya decidido y en uso (HU1) |
| Motor de ajedrez | Stockfish + python-chess | Ya decidido y en uso (HU2) |
| Modelo de aprendizaje | PyTorch | Entrenado en Google Colab (GPU gratuita); también es lo que ya entrena el clasificador de piezas de HU1 |
| Simulación del brazo | PyBullet | Ya decidido, en uso parcial (HU9) |
| Hardware del brazo 🔭 | ESP32 + PCA9685 | Ya decidido, para cuando llegue el kit |

### Dónde corre cada cosa — es un sistema híbrido, no todo en la nube

Esto es importante tenerlo claro desde ahora: **la cámara y el brazo tienen que estar
conectados físicamente a una máquina real** — no pueden vivir en un servidor en la nube. Por
eso el despliegue se piensa en dos partes:

**Local (la laptop del equipo — para la demo y para todo lo que toca hardware):**
- Backend completo (FastAPI) corriendo en `localhost`
- Base de datos PostgreSQL local
- Cámara conectada por USB
- Comunicación WiFi con el ESP32 del brazo (alcance de tesis)

**En la nube (opcional — para tener el proyecto accesible fuera de la demo en vivo):**
- Backend: Railway o Render (capa gratuita para proyectos chicos en Python)
- Base de datos: Supabase (Postgres gratis) o la misma capa gratuita de Railway
- Frontend: Vercel o Netlify (gratis, hechos para proyectos React)
- Checkpoints del modelo entrenado: Google Drive, o Hugging Face Hub (pensado
  específicamente para alojar modelos de IA, también gratis)

**Recomendación concreta para el día de la defensa:** correr todo en local. No conviene
depender de internet ni de que un servicio gratuito "despierte" a tiempo (Render, por ejemplo,
duerme los servicios inactivos) justo en el momento de mostrarlo al jurado. La versión en la
nube es un plus para demostrar que el software es desplegable — no el plan principal para el
día de la presentación.

---

## 7. Base de datos — sí va primero, pero solo lo mínimo de Sprint 1

Tenés razón en priorizar esto: si cada uno arranca a guardar datos a su manera, después hay
que rehacer todo. Pero **no hace falta diseñar las tablas completas del proyecto ahora** — eso
sería sobre-diseñar antes de necesitarlo. Para el sprint actual alcanza con 4 tablas:

```sql
CREATE TABLE participante (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL
);

CREATE TABLE sesion (
    id INTEGER PRIMARY KEY,
    facilitador TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dificultad INTEGER,       -- 0-20, nivel de Stockfish
    tipo_oponente TEXT        -- 'motor' | 'modelo' | 'participante' (ver Strategy, sección 4.1)
);

CREATE TABLE partida (
    id INTEGER PRIMARY KEY,
    participante_id INTEGER REFERENCES participante(id),
    sesion_id INTEGER REFERENCES sesion(id),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resultado TEXT,           -- 'en_curso' | 'blancas' | 'negras' | 'tablas'
    tipo TEXT                 -- 'fisica' | 'digital'
);

CREATE TABLE jugada (
    id INTEGER PRIMARY KEY,
    partida_id INTEGER REFERENCES partida(id),
    numero INTEGER,
    fen_antes TEXT NOT NULL,
    movimiento TEXT NOT NULL,     -- notación UCI, ej. "e2e4"
    decidido_por TEXT,            -- 'motor' | 'modelo' | 'jugador'
    tiempo_calculo_ms INTEGER,
    explicacion TEXT
);
```

**Quién la crea:** la persona que arranque primero con esta parte (recomendación: Luis Ángel,
ya que su HU3 también necesita leer/escribir partidas para el dataset). Las tablas que faltan
(`modelo_version` — con estado de promoción para el panel de administrador 🔭, `error_patron`,
`progreso`, `usuario` para el login 🔭) se agregan recién cuando lleguen a HU4, HU8 y a la
etapa de tesis correspondiente — no antes. **Hoy esto todavía no está creado:** las partidas
viven en memoria del proceso, detrás del `RepositorioPartidasEnMemoria` de la sección 4.3 — el
Repository ya está armado, solo falta la implementación con Postgres real.

---

## 8. Estructura del repositorio (destino acordado, migración pendiente)

```
ajedrez-robotico/
├── requirements.txt
├── backend/
│   ├── main.py                     # arranca la app FastAPI
│   ├── database.py                 # conexión a PostgreSQL (🔭, hoy no existe — todo en memoria)
│   ├── modelos/                    # capa de Modelos de datos
│   │   ├── partida.py
│   │   └── jugada.py
│   ├── esquemas/                   # capa de Esquemas (Pydantic)
│   │   ├── partida_esquema.py
│   │   └── jugada_esquema.py
│   ├── rutas/                      # capa de Rutas (Controlador)
│   │   ├── ruta_partida.py
│   │   └── ruta_jugada.py
│   ├── repositorios/               # patrón Repository (sección 4.3)
│   │   └── repositorio_partida.py
│   ├── servicios/                  # capa de Servicios (lógica real)
│   │   ├── estrategias/            # patrón Strategy + Factory (secciones 4.1, 4.2)
│   │   │   ├── estrategia_jugada.py
│   │   │   └── fabrica_estrategias.py
│   │   ├── partida/                # orquesta partidas jugables — HU10, trabajo adelantado
│   │   │   └── servicio_partida.py
│   │   ├── vision/                 # HU1 — Hebert (completa)
│   │   │   ├── modelo_piezas.py    # arquitectura de la CNN, compartida con training/
│   │   │   ├── tablero.py
│   │   │   ├── piezas.py
│   │   │   ├── reconocimiento.py
│   │   │   ├── camara.py            # RF06, captura desde cámara fija
│   │   │   └── deteccion_movimiento.py  # RF11, jugada por diff de FEN
│   │   ├── motor/                  # HU2 — Hebert
│   │   │   └── motor_ajedrez.py
│   │   ├── aprendizaje/            # HU3, HU4 — Luis Ángel (🔭 inferencia.py todavía no existe)
│   │   │   └── inferencia.py
│   │   ├── retroalimentacion/      # HU5 — Luis Ángel (🔭 no existe todavía; antes "educativo/")
│   │   └── simulacion/             # HU9 — Hebert
│   │       └── escena.py
├── training/
│   ├── colab_entrenamiento.ipynb   # 🔭 no existe todavía, HU3
│   ├── data_pipeline.py            # HU3, PGN de Lichess -> tensores
│   ├── dataset_piezas.py           # HU1, auto-etiqueta casillas para entrenar el clasificador
│   ├── entrenar_clasificador_piezas.py
│   └── checkpoints/                # ignorado por git
├── frontend/
│   ├── src/
│   │   ├── componentes/            # piezas reutilizables (tablero, panel, rostro)
│   │   ├── paginas/                # HU6 (visualización), HU10/HU11 (control)
│   │   └── servicios/              # llamadas a la API del backend
│   └── package.json
└── docs/
```

**Estado real hoy vs. este destino:** migrado. El árbol de arriba es exactamente cómo está
`backend/` hoy, con dos excepciones marcadas 🔭: `database.py` (no hay base de datos, todo en
memoria vía el Repository de la sección 4.3) y las carpetas de HU3/HU4/HU5
(`aprendizaje/`, `retroalimentacion/`) que todavía no tienen código porque esas HU no empezaron.

---

## 9. Convenciones de código

- **Nombres de variables, funciones y clases en español.** Las palabras propias del lenguaje
  (`def`, `class`, `return`, `async`) quedan en inglés porque son parte de Python, pero todo lo
  que ustedes nombran va en español:

  ```python
  def calcular_jugada(posicion_fen: str, nivel_dificultad: int) -> str:
      """
      Calcula la jugada del motor de ajedrez para una posición dada.

      posicion_fen: posición actual del tablero en notación FEN.
      nivel_dificultad: fuerza del motor, de 0 (principiante) a 20 (máximo).
      Devuelve la jugada elegida, en notación UCI (ej. "e2e4").
      """
      tablero = construir_tablero(posicion_fen)
      jugada_elegida = motor.jugar(tablero, nivel_dificultad)
      return jugada_elegida.uci()
  ```

- **Seguir PEP 8** (el estándar oficial de estilo en Python): funciones en `snake_case`, clases
  en `PascalCase`. Instalar `black` (`pip install black`) y correrlo antes de cada commit —
  formatea el código automáticamente, sin discusiones de estilo entre ustedes dos.
- **Docstring en cada función pública**, como en el ejemplo de arriba: qué recibe, qué
  devuelve.
- **Nombres descriptivos, no abreviados**: `tablero_reconocido` en vez de `tab_rec`,
  `nivel_dificultad` en vez de `nv_dif`.
- **Un archivo, una responsabilidad**: si un archivo de servicio supera las 200-300 líneas, es
  señal de que conviene separarlo en más archivos dentro de la misma carpeta.
- **Interfaces de Strategy/Repository como clases base abstractas** (`abc.ABC` +
  `@abstractmethod`) — es el estándar de Python para definir un contrato que varias clases
  deben cumplir, en vez de confiar en duck typing implícito para algo tan central.

---

## 10. Catálogo de Casos de Uso

Marca 🟢 = alcance del sprint actual (aunque sea en versión mínima); 🔭 = alcance de tesis.

### Actor: Jugador

**CU-J1 — Registrarse e iniciar sesión 🔭**
Descripción: el jugador crea una cuenta o inicia sesión para poder jugar y guardar su
historial. Precondición: ninguna. Flujo principal: (1) el jugador ingresa sus datos o
credenciales; (2) el sistema valida y autentica (JWT); (3) el sistema redirige al tablero.
Postcondición: sesión activa asociada al jugador. *No tiene HU asociada en el backlog de 11
HU — es contenido nuevo que agrega esta visión de tesis.*

**CU-J2 — Configurar y comenzar una partida online 🟢 (HU10, versión mínima)**
Descripción: el jugador elige contra qué/quién juega y con qué ajustes. Precondición: CU-J1
completado (🔭) / ninguna en la versión mínima actual. Flujo principal: (1) el jugador elige
tipo de oponente (Stockfish, modelo propio, u otro jugador); (2) elige nivel de dificultad;
(3) elige si activa la retroalimentación técnica; (4) el sistema crea la partida (`POST /partida`) y
muestra el tablero inicial. Postcondición: partida creada y en curso. **Hoy:** solo existe
elegir nivel; tipo de oponente y retroalimentación técnica faltan.

**CU-J3 — Jugar la partida 🟢 (ya construido, versión digital)**
Descripción: el jugador realiza jugadas (físicas, vía visión, o digitales) y el sistema
responde con su propia jugada. Flujo principal: (1) el jugador mueve una pieza; (2) el sistema
detecta/recibe el movimiento; (3) valida legalidad; (4) calcula la jugada de respuesta (vía la
estrategia de oponente activa); (5) si corresponde, ejecuta la jugada en el brazo (🔭); (6)
registra la jugada (🔭, vía Repository). Incluye: CU-S1 (percepción del tablero) cuando la
partida es física. **Hoy:** el flujo digital completo ya funciona (`POST /partida/{id}/mover`);
lo físico (visión en vivo + brazo) es HU1/HU9, parcial.

**CU-J4 — Recibir retroalimentación técnica de cada partida 🔭 (HU5)**
Sin empezar. Depende de HU3 (modelo entrenado). El sistema actúa como entrenador: compara cada
jugada contra la mejor alternativa de Stockfish e identifica el error concreto cometido. Es
agnóstico a quién fue el oponente — aplica igual a partidas contra el motor, el modelo, o (🔭)
contra otro jugador humano.

**CU-J5 — Ver historial y progreso propio 🔭 (HU8)**
Sin empezar — depende de que haya persistencia (Repository + base de datos).

**CU-J6 — Ver visualización del razonamiento del modelo en vivo 🔭 (HU6 ampliada)**
La versión mínima de HU6 (mostrar jugada + evaluación de Stockfish, cuando el oponente es el
motor) ya tiene su backend listo (`analizar_posicion`, `obtener_variaciones`). Cuando el oponente
es el modelo propio, este panel además muestra la jugada que decidió el modelo por su cuenta
junto a la comparación contra Stockfish (misma jugada o no, diferencia de evaluación) como
métrica de qué tan entrenado está — no como parte de cómo el modelo decidió. El mapa de atención
(Grad-CAM), la entropía y el WebSocket en vivo son la ampliación de tesis.

### Actor: Sistema (casos de uso internos)

**CU-S1 — Reconocer el tablero mediante visión 🟢 (HU1, hecho)**
Descripción: el sistema captura una imagen y la traduce a FEN. Flujo principal: (1) captura
imagen; (2) corrige perspectiva; (3) clasifica las 64 casillas; (4) compara con el FEN anterior
para detectar la jugada. Los 4 pasos están construidos y probados
(`backend/servicios/vision/`) — falta conectar (1) a un endpoint HTTP que dispare todo el flujo
de punta a punta ante una foto real (alcance de HU6, no de este caso de uso en sí).

**CU-S2 — Ejecutar la jugada en el brazo robótico 🔭 (HU9 ampliada)**
Hoy existe una versión mucho más chica: resaltar visualmente origen/destino en una escena
estática de PyBullet, sin cinemática ni pick-and-place.

**CU-S3 — Generar señal de entrenamiento 🔭**
Depende de que exista persistencia de partidas (Repository, sección 4.3).

### Actor: Administrador 🔭

**CU-A1 a CU-A6** — disparar reentrenamiento, evaluar/promover modelo, ver panel de errores,
configurar comportamiento del sistema, administrar sesiones/participantes, configurar
ejecución física. Ninguno tiene código construido todavía; son alcance de tesis, mapeados a
HU4, HU8, HU10 y HU11 en sus versiones ampliadas.

---

## 11. Catálogo de Requisitos Funcionales

Agrupados por módulo. Estado real a la fecha de esta revisión, no aspiracional.

**Módulo 1 — Motor de Ajedrez — 🟢 completo (HU2)**
RF01. Calcular la jugada mediante Stockfish (`calcular_jugada(fen, nivel)`). ✅
RF02. Configurar el nivel de dificultad del motor entre 0 y 20. ✅
RF03. Evaluar la posición en centipawns y detectar mate (`analizar_posicion`). ✅
RF04. Listar variantes candidatas mediante MultiPV (`obtener_variaciones`). ✅
RF05. Validar que toda jugada aceptada sea legal antes de ejecutarla. ✅

**Módulo 2 — Visión — ✅ hecho (HU1)**
RF06. Capturar la imagen del tablero mediante una cámara fija. ✅ `capturar_foto_tablero` (`cv2.VideoCapture`) — falta conectarlo a un endpoint/pantalla (HU6)
RF07. Corregir la perspectiva de la imagen a una vista cenital. ✅ `detectar_esquinas_tablero` + `enderezar_tablero`
RF08. Segmentar la imagen corregida en 64 casillas. ✅ `dividir_en_casillas`
RF09. Clasificar la pieza (o ausencia) en cada casilla mediante un modelo entrenado. ✅ CNN, 90% test — damas siguen siendo el punto débil
RF10. Generar el FEN correspondiente a la imagen reconocida. ✅ `reconocer_tablero`
RF11. Detectar el movimiento comparando el FEN anterior con el actual. ✅ `detectar_jugada(fen_antes, fen_despues)`

**Módulo 3 — Aprendizaje — 🟨 en curso (HU3), resto sin empezar (HU4)**
RF12. Pipeline que transforme PGN en tensores y etiquetas. ✅ `training/data_pipeline.py`
RF13. Entrenar un modelo por bandas de nivel/estilo. ⬜
RF14. Reentrenar en lotes controlados y versionados. ⬜
RF15. Evaluar cada versión candidata antes de promoverla. ⬜
RF16. Guardar checkpoints versionados en Drive. ⬜
RF17. No modificar el modelo en producción durante una partida. ✅ (por diseño — regla de `CLAUDE.md`, todavía no hay "producción" que modificar)

**Módulo 4 — Retroalimentación Técnica de Partidas (antes "Educativo") — ⬜ sin empezar (HU5)**
RF18. Comparar cada jugada del jugador contra la mejor alternativa calculada por el motor
(pérdida en centipawns), para identificar el error específico cometido. ⬜
RF19. Explicar en lenguaje comprensible qué principio de juego debió aplicarse en esa jugada
(desarrollo, control del centro, capturas, jaque mate). ⬜
RF20. Transmitir principios básicos del ajedrez adaptados al nivel del participante. ⬜

*Nota de diseño:* este servicio debe leer genéricamente de la tabla `jugada` por
`partida_id`, sin asumir quién fue el oponente. El análisis comparativo contra Stockfish es
agnóstico a si la partida fue contra el motor, contra el modelo propio, o (🔭, cuando exista
la función de partidas entre jugadores) contra otra persona — el mismo servicio sirve para los
tres casos sin desarrollo adicional. Esto es lo que reemplaza al rol de "entrenador humano" que
aparecía en versiones anteriores de la propuesta: acá el entrenador es la propia IA dando
feedback después de cada partida, no un rol humano separado en el sistema.

**Módulo 5 — Visualización del Razonamiento — 🟨 base mínima, resto 🔭 (HU6 ampliada)**
RF21. Exponer jugadas candidatas con probabilidad. Parcial — `obtener_variaciones` da candidatas de Stockfish (para partidas contra el motor); las candidatas del modelo propio, con su comparación contra Stockfish como métrica de entrenamiento (no como validación), quedan para cuando HU3/HU4 den un modelo entrenado.
RF22-RF24 (Grad-CAM, entropía, WebSocket en vivo). ⬜ 🔭

**Módulo 6 — Control del Brazo — 🟨 base mínima, resto 🔭 (HU9 ampliada)**
RF25-RF27, RF29 (calibración XYZ, cinemática inversa, pick-and-place, validar en simulador). ⬜/🟨 —
hoy solo existe `resaltar_jugada` (marcar visualmente origen/destino), sin cinemática real.
RF28 (alternar simulado/real sin cambios en el resto — Strategy 4.1). Interfaz a definir, sin implementar.

**Módulo 7 — Partidas Online — 🟢 mayormente construido (trabajo adelantado + HU10)**
RF30. Crear y consultar una partida. ✅
RF31. Seleccionar tipo de oponente y nivel al crear. Parcial — solo nivel, falta tipo de oponente (Strategy 4.1).
RF32. Validar y aplicar cada movimiento. ✅
RF33. Actualizar el tablero en tiempo real para todos los clientes conectados. ⬜ 🔭 (hoy es de un solo cliente, sin WebSocket)
RF34. Registrar cada jugada como dato candidato para reentrenamiento. ⬜ (depende de Repository + persistencia)

**Módulo 8 — Seguimiento y Progreso — ⬜ sin empezar (HU8)**
RF35-RF37.

**Módulo 9 — Administración — ⬜ sin empezar (HU10/HU11, panel completo es 🔭)**
RF38-RF42.

**Módulo 10 — Plataforma y Comunidad — 🔭 visión de tesis, sin empezar**
RF43. Registrar un jugador y mantener su perfil con historial de partidas y progreso. ⬜ 🔭
RF44. Ofrecer una evaluación inicial (ejercicios o partidas de calibración) para estimar el
nivel de un jugador nuevo. ⬜ 🔭
RF45. Emparejar a dos jugadores humanos de nivel similar para una partida (matchmaking). ⬜ 🔭
RF46. Mantener una clasificación (ranking) en base al desempeño en partidas y competencias. ⬜ 🔭
RF47. Organizar torneos, definir categorías de participación y registrar resultados. ⬜ 🔭
RF48. Ofrecer a la Asociación un panel para publicar eventos y consultar participación
agregada. ⬜ 🔭

---

## 12. Notas de Factibilidad

- El mapa de atención (Grad-CAM) depende de que la arquitectura de la CNN tenga capas
  convolucionales identificables; si la arquitectura cambia radicalmente, hay que revisar que
  la técnica siga aplicando. Aplica al clasificador de piezas de HU1 y a un futuro modelo de
  HU3/HU4 — ambos son CNN, así que la técnica es viable en principio.
- La personalización por oponente individual (que el modelo aprenda el estilo de una persona
  específica) no es viable en el tiempo de esta tesis por volumen de datos insuficiente por
  jugador; se adopta el enfoque por bandas de nivel/estilo (tipo Maia) como alternativa
  acotada, y la personalización 1-a-1 queda documentada como trabajo futuro.
- Los módulos de Visualización del Razonamiento y Control del Brazo amplían el alcance
  original de HU6 y HU9 respectivamente — no subestimar su esfuerzo si se decide encararlos
  ya: son fácilmente la mitad del trabajo restante de todo el proyecto.

---

## 13. Las 11 HU del sprint actual, divididas por sprint y persona

| Sprint | HU | Descripción | Puntos | Responsable | Depende de | Módulo (sección 11) |
|---|---|---|---|---|---|---|
| **1** | HU1 | Reconocimiento de Tablero y Piezas | 8 | Hebert | — | Módulo 2 |
| **1** | HU2 | Motor de Jugadas y Niveles de Dificultad | 3 | Hebert | — | Módulo 1 |
| **1** | HU3 | Entrenamiento del Modelo con Partidas de Referencia | 5 | Luis Ángel | — | Módulo 3 |
| **2** | HU6 | Visualización del Razonamiento en Tiempo Real | 5 | Hebert | HU1 | Módulo 5 |
| **2** | HU4 | Reentrenamiento y Evaluación del Modelo | 5 | Luis Ángel | HU3 | Módulo 3 |
| **2** | HU5 | Retroalimentación Técnica de Partidas | 5 | Luis Ángel | HU3 | Módulo 4 |
| **2** | HU10 | Configuración de Partida | 3 | Luis Ángel | HU2 | Módulo 7, 9 |
| **3** | HU9 | Interconexión con el Brazo Robótico (simulado) | 8 | Hebert | HU2 | Módulo 6 |
| **3** | HU7 | Rostro y Expresiones del Sistema | 3 | Luis Ángel | HU6 | — |
| **3** | HU8 | Panel de Progreso | 3 | Luis Ángel | — | Módulo 8 |
| **3** | HU11 | Administración de Sesiones y Participantes | 3 | Luis Ángel | — | Módulo 9 |

**Por qué este orden:** HU1 y HU2 no dependen de nada, así que arrancan ya. HU6 (visualización)
necesita que HU1 exista primero para tener algo que mostrar. HU9 (el brazo) va al final a
propósito — es la pieza de mayor riesgo (8 puntos, depende del kit y del simulador), y conviene
tener todo lo demás sólido antes de meterse ahí.

Estado real de avance — ver `docs/plan_sprints.md`, que es el tablero de seguimiento vivo (se
actualiza a medida que se completan tareas); este documento no repite ese detalle para no
tener dos lugares que puedan desincronizarse.

---

## 14. HU2 en detalle — el motor de ajedrez (tarea de Hebert)

**Ya hecho.** Queda como referencia de cómo se construyó. La idea central: no programás un
motor de ajedrez — integrás uno que ya existe (Stockfish) y le construís una capa alrededor.

### Pasos que se siguieron

1. **Instalar Stockfish** (el programa en sí, no la librería de Python) y anotar la ruta.
2. **Instalar `python-chess`** (`pip install chess`) — no instala Stockfish, solo permite
   hablarle desde Python.
3. **Escribir el servicio** (`backend/servicios/motor/motor_ajedrez.py`):
   ```python
   import chess
   import chess.engine

   def calcular_jugada(fen: str, nivel: int = 20, tiempo_limite: float = 1.0) -> str:
       tablero = chess.Board(fen)
       with chess.engine.SimpleEngine.popen_uci("stockfish") as motor:
           motor.configure({"Skill Level": nivel})
           resultado = motor.play(tablero, chess.engine.Limit(time=tiempo_limite))
           return tablero.san(resultado.move)
   ```
4. **Probado con posiciones conocidas** (aperturas + mate en 1) antes de conectarlo a nada más.
5. **Expuesto vía rutas** — hoy `POST /jugada` y `POST /analisis` en `backend/main.py`.

### Qué NO hacer todavía en HU2

- No mezclar el modelo de aprendizaje acá — HU2 es solo Stockfish.
- No preocuparse por el brazo ni por PyBullet — eso es HU9.
- No optimizar el tiempo de cálculo — 1 segundo por jugada ya es suficiente para la demo.

---

## 15. HU1 en detalle — visión (Hebert)

**En curso.** Servicio `reconocer_tablero(imagen) -> fen` en `backend/servicios/vision/`:

- `tablero.py` — `detectar_esquinas_tablero` (contorno de 4 lados vía Canny + approxPolyDP),
  `enderezar_tablero` (perspectiva), `dividir_en_casillas`. Probado contra fotos reales del
  dataset público "Chess Pieces" de Roboflow (licencia dominio público,
  `training/dataset_tablero/`, ignorado por git).
- `modelo_piezas.py` — arquitectura de la CNN y su preprocesamiento, compartidos entre
  `training/entrenar_clasificador_piezas.py` (la entrena) y `piezas.py` (la usa en producción),
  para que ninguno de los dos dependa del otro.
- `piezas.py` — carga el checkpoint entrenado y clasifica una casilla. 90% accuracy en test tras
  balancear clases; las damas (la clase con menos ejemplos) siguen siendo la pieza menos
  confiable.
- `reconocimiento.py` — junta todo en `reconocer_tablero(imagen, turno="w") -> fen`. El turno
  se recibe como parámetro porque una sola foto no alcanza para saber de quién es; enroque y
  al paso quedan siempre en su valor por defecto por la misma razón.
- `camara.py` — `capturar_foto_tablero(indice_camara)` (RF06), vía `cv2.VideoCapture`. Probado
  contra la cámara real de la máquina de Hebert, no solo el caso de error.
- `deteccion_movimiento.py` — `detectar_jugada(fen_antes, fen_despues)` (RF11): prueba todas las
  jugadas legales de la posición "antes" y devuelve la que reproduce exactamente la ubicación
  de piezas de "después". Sin IA — más confiable que tratar de leer la jugada de la imagen.

**HU1 completa** en el sentido de que cada etapa (esquinas, clasificación, armado de FEN, diff
de jugada) está construida y probada por separado. **Limitación real descubierta después:** no
hay ningún test automatizado que corra `reconocer_tablero` de punta a punta contra una foto real
con el clasificador entrenado — `test_reconocimiento.py` solo prueba el armado del FEN con datos
inventados a mano. Al revisar ~40 fotos reales del dataset de test de Roboflow (el mismo dominio
con el que se entrenó, no un tablero ajeno) ninguna reconstruyó una posición coherente de punta a
punta — el 90% de accuracy documentado es por casilla individual, no del tablero completo
reconstruido. Reconocer un tablero jugable de forma consistente, incluso en el dominio de
entrenamiento, queda como trabajo pendiente real, no cerrado como sugería este documento antes.

---

## 16. HU3 en detalle — entrenamiento del modelo (Luis Ángel)

1. Bajar un mes de partidas de database.lichess.org (no el dataset completo). ✅
2. `training/data_pipeline.py`: usa `python-chess` para leer el PGN, y por cada posición
   jugada genera el tablero antes (como tensor) + la jugada del humano (como etiqueta). ✅
3. Subir esto a **Google Colab** (GPU gratis) y probar con un subconjunto chico (100-200
   partidas) antes de escalar al mes completo. ⬜ pendiente
4. Entrenar una primera versión simple del modelo — el objetivo es que el pipeline funcione de
   punta a punta, no lograr precisión alta todavía. ⬜ pendiente
5. **Guardar los checkpoints en Google Drive**, no solo en la sesión de Colab. ⬜ pendiente

---

## 17. Sobre el simulador y el brazo — HU9, no es para ahora

Cuando llegue el momento de encarar esto (Sprint 3):

- El simulador es **PyBullet** (`pip install pybullet`), ya en uso — hoy con una escena
  estática de tablero 3D que resalta origen/destino (`backend/servicios/simulacion/escena.py`),
  sin brazo articulado.
- PyBullet necesita un archivo **URDF** (descripción del brazo) — el kit no lo trae listo, hay
  que construirlo. Mientras no esté el URDF exacto, se puede probar la lógica de control con
  uno de los brazos de ejemplo que ya vienen incluidos en PyBullet.
- El patrón Strategy que corresponde acá es el **ejecutor de movimientos** (sección 4.1) —
  `EjecutorSimulado` ya existe en espíritu (`resaltar_jugada`); `EjecutorReal` (ESP32 + PCA9685)
  es alcance de tesis, no de este sprint.

---

## 18. Cómo no interferirse — reglas de trabajo en paralelo

- **Una rama de git por HU**, no por persona: `feature/hu1-vision`, `feature/hu2-motor`,
  `feature/hu3-modelo`.
- **El contrato de datos (FEN) es intocable** sin avisar al otro.
- **La base de datos la modifica una sola persona por vez** (usar migraciones, no editar el
  esquema a mano cada uno por su lado).
- Revisión cruzada antes de mergear a la rama principal.

---

## 19. Checklist de cierre del sprint actual

- [x] `calcular_jugada` funciona y devuelve jugadas legales para al menos 10 posiciones de
      prueba distintas (Hebert).
- [x] `reconocer_tablero` reconoce un tablero de prueba real de punta a punta (Hebert) — con
      la limitación conocida de las damas, documentada en `docs/plan_sprints.md`.
- [ ] Pipeline de datos de Lichess corre de punta a punta en Colab con un subconjunto chico, y
      hay al menos una primera versión del modelo entrenada y guardada en Drive (Luis Ángel).
- [ ] Las 4 tablas de la base de datos existen y las jugadas de prueba quedan guardadas ahí.
- [x] Los dos servicios (visión y motor) ya se hablan entre sí usando FEN como formato común.
