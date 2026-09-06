# Plan de Implementación Completo — Brazo Robótico con IA para Ajedrez

Equipo: Suárez Burgos Hebert · Arce Kao Luis Ángel

> **Principio rector: hay un solo software.** Este plan sirve para programar, sin importar
> si documentan primero para SW2 o para Taller de Grado I — el código, la base de datos y
> el orden de trabajo son los mismos. Lo único que cambia entre materias es el formato del
> documento que llenan *después* de programar, nunca el software en sí.

---

## 1. Antes de escribir código: qué deciden juntos, una sola vez

Esto se hace en una sola sesión de 1-2 horas, los dos juntos, antes de que cada uno arranque
por su lado. Si no lo hacen, van a terminar con formatos de datos incompatibles entre el
módulo de Hebert y el de Luis Ángel.

- [ ] Crear el repositorio en GitHub (uno solo, no uno por persona).
- [ ] Acordar el **contrato de datos entre módulos**: ¿en qué formato exacto se pasan un
      tablero entre el módulo de visión y el módulo de motor? Recomendación: **FEN**
      (Forsyth-Edwards Notation), el estándar de ajedrez — es una sola línea de texto,
      ejemplo: `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`. Todo el proyecto
      habla en FEN entre sí; nadie inventa su propio formato de tablero.
- [ ] Crear el archivo `requirements.txt` vacío y decidir juntos cada versión a medida que
      la agreguen (no dejar ninguna dependencia "sin fijar").
- [ ] Crear las 4 tablas mínimas de la base de datos (sección 4) — esto lo hace una sola
      persona, no las dos por separado, para evitar migraciones en conflicto.

---

## 2. Arquitectura del Software

### Patrón: Arquitectura en Capas (la versión moderna de MVC para una API)

MVC clásico se pensó para cuando el propio servidor arma el HTML de la página (Modelo-Vista-
Controlador, todo junto). Acá el backend es una API que no arma HTML — el frontend es una
aplicación aparte que le consulta datos. El patrón que corresponde a esto es una
**arquitectura en capas**, que en el fondo es la misma idea de MVC, solo que separada de
forma más clara. Así se las recomiendo organizar:

| Capa | Equivalente en MVC | Qué hace | Carpeta |
|---|---|---|---|
| Rutas (routers) | Controlador | Recibe la petición HTTP, valida los datos de entrada, llama al servicio correspondiente | `backend/routers/` |
| Servicios | Modelo (lógica) | Acá vive la lógica real del negocio: `calcular_jugada`, `reconocer_tablero`, `entrenar_modelo` | `backend/services/` |
| Esquemas | — (DTO) | Define la forma exacta de los datos que entran y salen de cada endpoint (con Pydantic) | `backend/schemas/` |
| Modelos de datos | Modelo (datos) | Representa las tablas de la base de datos | `backend/models/` |
| Frontend (React) | Vista | Lo que ve y usa el facilitador o el participante | `frontend/` |

**Cómo se construye cada HU con esto:** una ruta nueva → llama a un servicio nuevo → (si
hace falta) usa o crea un modelo de datos → el frontend consume esa ruta desde una pantalla.
Siempre en ese orden, de adentro hacia afuera.

### Por qué esta arquitectura y no otra

- Separa "qué pide el usuario" (rutas) de "qué hace el sistema" (servicios): si mañana
  cambian de cámara o prueban otro motor de ajedrez, tocan un solo archivo de servicio, no
  todo el sistema.
- Encaja directo con lo que pide la materia de SW2: el "Diagrama de Paquetes organizado en
  capas" que exige el Capítulo 3 es literalmente este esquema, dibujado.
- No es sobre-ingeniería: para 2 personas y unas semanas, microservicios o arquitecturas más
  complejas solo agregarían trabajo sin necesidad real.

---

## 3. Stack Tecnológico Completo

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Ya decidido — rápido de escribir, documentación automática (Swagger/OpenAPI), tipado con Pydantic |
| Frontend | React (con Vite) | Mismo stack que usan los proyectos de referencia de la materia; permite actualización en vivo para HU6 |
| Tiempo real | WebSockets (FastAPI ya los trae) | Necesario para HU6 — mostrar jugada y análisis en vivo sin recargar la página |
| Base de datos | PostgreSQL | El equipo ya tiene experiencia con él (proyecto anterior de semáforos) |
| Visión por computadora | OpenCV | Ya decidido |
| Motor de ajedrez | Stockfish + python-chess | Ya decidido |
| Modelo de aprendizaje | PyTorch | Entrenado en Google Colab (GPU gratuita) |
| Simulación del brazo | PyBullet | Ya decidido, para HU9 (Sprint 3) |
| Hardware del brazo | ESP32 + PCA9685 | Ya decidido |

### Dónde corre cada cosa — es un sistema híbrido, no todo en la nube

Esto es importante tenerlo claro desde ahora: **la cámara y el brazo tienen que estar
conectados físicamente a una máquina real** — no pueden vivir en un servidor en la nube. Por
eso el despliegue se piensa en dos partes:

**Local (la laptop del equipo — para la demo y para todo lo que toca hardware):**
- Backend completo (FastAPI) corriendo en `localhost`
- Base de datos PostgreSQL local
- Cámara conectada por USB
- Comunicación WiFi con el ESP32 del brazo (recién en Sprint 3)

**En la nube (opcional — para tener el proyecto accesible fuera de la demo en vivo):**
- Backend: Railway o Render (capa gratuita para proyectos chicos en Python)
- Base de datos: Supabase (Postgres gratis) o la misma capa gratuita de Railway
- Frontend: Vercel o Netlify (gratis, hechos para proyectos React)
- Checkpoints del modelo entrenado: Google Drive, o Hugging Face Hub (pensado
  específicamente para alojar modelos de IA, también gratis)

**Recomendación concreta para el día de la defensa:** correr todo en local. No conviene
depender de internet ni de que un servicio gratuito "despierte" a tiempo (Render, por
ejemplo, duerme los servicios inactivos) justo en el momento de mostrarlo al jurado. La
versión en la nube es un plus para demostrar que el software es desplegable — no el plan
principal para el día de la presentación.

---

## 4. Base de datos — sí va primero, pero solo lo mínimo de Sprint 1

Tenés razón en priorizar esto: si cada uno arranca a guardar datos a su manera, después hay
que rehacer todo. Pero **no hace falta diseñar las 8 tablas completas del proyecto ahora** —
eso sería sobre-diseñar antes de necesitarlo. Para Sprint 1 alcanza con 4 tablas:

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
    tipo_oponente TEXT        -- 'motor' | 'modelo' | 'participante'
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

**Quién la crea:** la persona que arranque primero con el repo (recomendación: Luis Ángel,
ya que su HU3 también necesita leer/escribir partidas para el dataset). Las tablas que faltan
(`modelo_version`, `error_patron`, `progreso`) se agregan recién cuando lleguen a HU4 y HU8 —
no antes.

---

## 5. Estructura del repositorio (reflejando las capas de la sección 2)

```
ajedrez-robotico/
├── requirements.txt
├── backend/
│   ├── main.py                     # arranca la app FastAPI
│   ├── database.py                 # conexión a PostgreSQL
│   ├── modelos/                    # capa de Modelos de datos
│   │   ├── partida.py
│   │   └── jugada.py
│   ├── esquemas/                   # capa de Esquemas (Pydantic)
│   │   ├── partida_esquema.py
│   │   └── jugada_esquema.py
│   ├── rutas/                      # capa de Rutas (Controlador)
│   │   ├── ruta_partida.py
│   │   └── ruta_jugada.py
│   ├── servicios/                  # capa de Servicios (lógica real)
│   │   ├── vision/                 # HU1 — Hebert
│   │   │   └── reconocimiento.py
│   │   ├── motor/                  # HU2 — Hebert
│   │   │   └── motor_ajedrez.py
│   │   ├── aprendizaje/            # HU3, HU4 — Luis Ángel
│   │   │   ├── pipeline_datos.py
│   │   │   └── inferencia.py
│   │   ├── educativo/              # HU5 — Luis Ángel
│   │   └── simulacion/             # HU9 — Hebert (Sprint 3)
├── training/
│   ├── colab_entrenamiento.ipynb
│   └── checkpoints/
├── frontend/
│   ├── src/
│   │   ├── componentes/            # piezas reutilizables (tablero, panel, rostro)
│   │   ├── paginas/                # HU6 (visualización), HU10/HU11 (control)
│   │   └── servicios/              # llamadas a la API del backend
│   └── package.json
└── docs/
```

---

## 6. Convenciones de código

- **Nombres de variables, funciones y clases en español.** Las palabras propias del
  lenguaje (`def`, `class`, `return`, `async`) quedan en inglés porque son parte de Python,
  pero todo lo que ustedes nombran va en español:

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

- **Seguir PEP 8** (el estándar oficial de estilo en Python): funciones en `snake_case`,
  clases en `PascalCase`. Instalar `black` (`pip install black`) y correrlo antes de cada
  commit — formatea el código automáticamente, sin discusiones de estilo entre ustedes dos.
- **Docstring en cada función pública**, como en el ejemplo de arriba: qué recibe, qué
  devuelve.
- **Nombres descriptivos, no abreviados**: `tablero_reconocido` en vez de `tab_rec`,
  `nivel_dificultad` en vez de `nv_dif`.
- **Un archivo, una responsabilidad**: si un archivo de servicio supera las 200-300 líneas,
  es señal de que conviene separarlo en más archivos dentro de la misma carpeta.

---

## 7. Las 11 HU, divididas por sprint y persona (plan completo)

| Sprint | HU | Descripción | Puntos | Responsable | Depende de |
|---|---|---|---|---|---|
| **1** | HU1 | Reconocimiento de Tablero y Piezas | 8 | Hebert | — |
| **1** | HU2 | Motor de Jugadas y Niveles de Dificultad | 3 | Hebert | — |
| **1** | HU3 | Entrenamiento del Modelo con Partidas de Referencia | 5 | Luis Ángel | — |
| **2** | HU6 | Visualización del Razonamiento en Tiempo Real | 5 | Hebert | HU1 |
| **2** | HU4 | Reentrenamiento y Evaluación del Modelo | 5 | Luis Ángel | HU3 |
| **2** | HU5 | Modo Educativo | 5 | Luis Ángel | HU3 |
| **2** | HU10 | Configuración de Partida | 3 | Luis Ángel | HU2 |
| **3** | HU9 | Interconexión con el Brazo Robótico (simulado) | 8 | Hebert | HU2 |
| **3** | HU7 | Rostro y Expresiones del Sistema | 3 | Luis Ángel | HU6 |
| **3** | HU8 | Panel de Progreso | 3 | Luis Ángel | — |
| **3** | HU11 | Administración de Sesiones y Participantes | 3 | Luis Ángel | — |

**Por qué este orden:** HU1 y HU2 no dependen de nada, así que arrancan ya. HU6
(visualización) necesita que HU1 exista primero para tener algo que mostrar. HU9 (el brazo)
va al final a propósito — es la pieza de mayor riesgo (8 puntos, depende del kit y del
simulador), y conviene tener todo lo demás sólido antes de meterse ahí.

---

## 8. HU2 en detalle — el motor de ajedrez (tarea de Hebert)

Vos preguntaste específicamente qué es esto, así que vamos al detalle. **La idea central: no
programás un motor de ajedrez — integrás uno que ya existe (Stockfish) y le construís una
capa alrededor.**

### Qué tenés que lograr al final

Un servicio que reciba una posición de tablero y devuelva la jugada que hay que hacer:

```python
def calcular_jugada(posicion_fen: str, nivel_dificultad: int) -> str:
    """
    posicion_fen: posición actual del tablero en notación FEN
    nivel_dificultad: 0-20, qué tan fuerte juega Stockfish
    devuelve: la jugada elegida, en notación UCI (ej. "e2e4")
    """
```

### Pasos concretos

1. **Instalar Stockfish** (el programa en sí, no la librería de Python):
   - Linux: `sudo apt install stockfish`
   - O bajar el binario directo de stockfishchess.org/download/
   - Anotar la ruta donde quedó instalado (ej. `/usr/games/stockfish`)

2. **Instalar la librería que lo conecta con Python:**
   ```bash
   pip install chess
   ```
   Esto es `python-chess` — no instala Stockfish, solo permite hablarle desde Python.

3. **Escribir el servicio mínimo** (`backend/servicios/motor/motor_ajedrez.py`):
   ```python
   import chess
   import chess.engine

   RUTA_STOCKFISH = "/usr/games/stockfish"  # ajustar a tu instalación

   def calcular_jugada(posicion_fen: str, nivel_dificultad: int) -> str:
       tablero = chess.Board(posicion_fen)
       with chess.engine.SimpleEngine.popen_uci(RUTA_STOCKFISH) as motor:
           motor.configure({"Skill Level": nivel_dificultad})  # 0 a 20
           resultado = motor.play(tablero, chess.engine.Limit(time=2.0))
           return resultado.move.uci()
   ```

4. **Probarlo con posiciones conocidas** antes de conectarlo a nada más:
   ```python
   posicion_inicial = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
   print(calcular_jugada(posicion_inicial, nivel_dificultad=10))
   ```

5. **Exponerlo en una ruta** (`backend/rutas/ruta_jugada.py`):
   ```python
   from fastapi import APIRouter
   from backend.servicios.motor.motor_ajedrez import calcular_jugada

   router = APIRouter()

   @router.post("/partida/{id_partida}/jugada")
   def endpoint_calcular_jugada(id_partida: int, posicion_fen: str, nivel_dificultad: int):
       jugada = calcular_jugada(posicion_fen, nivel_dificultad)
       # guardar en la tabla `jugada` (decidido_por='motor')
       return {"jugada": jugada}
   ```

6. **Guardar cada jugada en la tabla `jugada`** — esto alimenta después el dataset de HU4 y
   el panel de progreso de HU8.

### Qué NO hacer todavía en HU2

- No mezclar el modelo de aprendizaje acá — HU2 es solo Stockfish. El modelo (HU3) es un
  servicio aparte que se conecta después.
- No te preocupes por el brazo ni por PyBullet — eso es HU9, sprint 3.
- No optimices el tiempo de cálculo todavía — 2 segundos por jugada es el objetivo ya
  definido en el PAPs, no hace falta afinar más por ahora.

---

## 9. HU1 en detalle — resumen (Hebert, en paralelo o después de HU2)

- Instalar OpenCV: `pip install opencv-python`
- Armar un set de 15-20 fotos de un tablero real en distintas condiciones de luz.
- Servicio `reconocer_tablero(imagen) -> str`: detecta las 64 casillas (transformación de
  perspectiva + grilla), identifica qué pieza hay en cada una, arma el string FEN.
- No hace falta reconocimiento perfecto en el primer intento — empezá con un tablero con
  piezas bien diferenciadas antes de casos difíciles.

---

## 10. HU3 en detalle — para que Luis Ángel tenga su guía también

1. Bajar un mes de partidas de database.lichess.org (no el dataset completo).
2. Escribir `pipeline_datos.py`: usa `python-chess` para leer el PGN, y por cada posición
   jugada genera el tablero antes (como tensor) + la jugada del humano (como etiqueta).
3. Subir esto a **Google Colab** (GPU gratis) y probar con un subconjunto chico (100-200
   partidas) antes de escalar al mes completo.
4. Entrenar una primera versión simple del modelo — el objetivo de Sprint 1 es que el
   pipeline funcione de punta a punta, no lograr precisión alta todavía.
5. **Guardar los checkpoints en Google Drive**, no solo en la sesión de Colab.

---

## 11. Sobre el simulador del brazo — no es para ahora

Esto es HU9, **Sprint 3**, no Sprint 1. Cuando llegues ahí:

- El simulador es **PyBullet** (`pip install pybullet`), ya decidido.
- PyBullet necesita un archivo **URDF** (descripción del brazo: segmentos, medidas,
  articulaciones) — el kit de FabriCreator no lo trae listo, hay que construirlo.
- **Mientras no tengan el URDF exacto**, se puede probar la lógica de control con uno de los
  brazos de ejemplo que ya vienen incluidos en PyBullet, y cambiarlo por el real cuando esté
  listo. No hace falta esperar el kit para empezar a programar esta parte.

---

## 12. Cómo no interferirse — reglas de trabajo en paralelo

- **Una rama de git por HU**, no por persona: `feature/hu1-vision`, `feature/hu2-motor`,
  `feature/hu3-modelo`.
- **El contrato de datos (FEN) es intocable** sin avisar al otro.
- **La base de datos la modifica una sola persona por vez** (usar migraciones, no editar el
  esquema a mano cada uno por su lado).
- Revisión cruzada antes de mergear a la rama principal.

---

## 13. Checklist de cierre de Sprint 1

- [ ] `calcular_jugada` funciona y devuelve jugadas legales para al menos 10 posiciones de
      prueba distintas (Hebert).
- [ ] `reconocer_tablero` reconoce correctamente al menos un tablero de prueba fijo (Hebert).
- [ ] Pipeline de datos de Lichess corre de punta a punta con un subconjunto chico, y hay
      al menos una primera versión del modelo entrenada y guardada en Drive (Luis Ángel).
- [ ] Las 4 tablas de la base de datos existen y las jugadas de prueba quedan guardadas ahí.
- [ ] Los dos servicios (visión y motor) ya se hablan entre sí usando FEN como formato común.
