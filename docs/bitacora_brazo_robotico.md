# Bitácora técnica — Brazo Robótico (HU9)

> Registro corriente de avance para HU9 (simulador 3D + integración con el brazo
> robótico). No es un documento académico pulido: son notas técnicas fechadas, con
> los datos concretos (nombres de archivo, valores exactos, decisiones tomadas y por
> qué) para no perder detalle antes de redactar el capítulo correspondiente del
> documento de Taller de Grado. El documento de marco teórico
> (`docs/marco_teorico_ia_entrenamiento.md`) cubre solo el modelo de IA de decisión;
> esta bitácora cubre todo lo demás: simulador PyBullet, piezas 3D, puente 2D↔3D, y
> la integración con el brazo real (Dobot CR5AS).

---

## 2026-09-26 — Piezas de ajedrez en 3D para el simulador PyBullet

**Contexto:** el simulador (`backend/servicios/simulacion/escena.py`) hasta ahora
dibujaba el tablero pero no tenía piezas 3D reales.

**Generación (Meshy.ai).** Se generaron las 6 piezas de un set Staunton (rey, reina,
alfil, caballo, torre, peón) con Meshy, en un solo color para no gastar créditos de
más. Los modelos crudos salieron pesados: entre 98,000 y 365,000 caras y texturas de
22–24 MB cada una — inviable para cargarlos en tiempo real en PyBullet.

**Optimización (Blender headless, `blender.exe --background --python script.py`).**
- Decimación vía modificador `DECIMATE` aplicado con `bpy.ops.object.modifier_apply`:
  las 6 piezas quedaron en **2,500 caras** cada una.
- Texturas reescaladas a 1024×1024 y reexportadas como JPEG calidad 88 (Pillow):
  quedaron todas por debajo de ~181 KB.
- Segunda variante de color ("oscuro", madera oscura) generada **sin gastar créditos
  extra de Meshy**: manipulación directa del material/textura en Blender + PIL
  (`ImageEnhance.Brightness`/`ImageEnhance.Color` + transformación punto a punto por
  canal RGB) a partir del mismo modelo base "claro".
- Resultado final: `backend/servicios/simulacion/assets/piezas/{claro,oscuro}/
  {rey,reina,alfil,caballo,torre,peon}.{obj,mtl,jpg}` — 36 archivos, ~4 MB en total.

**Escala y orientación — verificado, no adivinado.**
- `ESCALA_PIEZA = 16.0`: el rey (la pieza de mayor base) mide ~0.045 m de footprint en
  el .obj crudo; ×16 da ~72% del ancho de una casilla de 1.0 unidad, que es un
  tamaño visualmente razonable sin que las piezas se toquen entre casillas.
- `ROTACION_MALLA_Y_ARRIBA_A_Z_ARRIBA = (sin(π/4), 0, 0, cos(π/4))`: un cuaternión de
  +90° sobre el eje X. Blender exporta OBJ con la convención "Y arriba"; PyBullet
  espera mundo "Z arriba". Sin esta corrección las piezas aparecían acostadas de
  lado.
- Verificación independiente en dos vías antes de dar esto por bueno: (a) cálculo a
  mano de la matriz de rotación equivalente al cuaternión, y (b) un render de prueba
  en Blender desde cero reproduciendo la misma transformación, para confirmar que el
  resultado visual coincidía con lo esperado. No se confió únicamente en que
  "cargó sin error" en PyBullet.

**Integración en `escena.py`.** Funciones nuevas: `cargar_formas_visuales_piezas`
(carga las 12 variantes .obj una sola vez como visual shapes de PyBullet),
`_crear_piezas_desde_tablero`, `_crear_piezas_posicion_inicial`, y
`sincronizar_piezas(client_id, piezas_actuales, tablero, formas_visuales)`. Esta
última hace teardown/rebuild completo (`p.removeBody` de todas las piezas actuales +
recreación desde un `chess.Board()` arbitrario) en vez de diffing — decisión
consciente: el ajedrez es por turnos, no hay necesidad de animar transiciones
incrementales por ahora, y así el código queda mucho más simple. `crear_escena()`
ahora devuelve `(client_id, casillas, piezas)` en vez de `(client_id, casillas)`.

**Tests:** 9 tests en `backend/servicios/simulacion/test_escena.py`, incluyendo
casos de captura (31 piezas tras una captura) y de sincronizaciones repetidas
seguidas (verifica que no queden "bodies" huérfanos en PyBullet). Corridos y en
verde contra el entorno conda real (ver sección de entorno más abajo).

---

## 2026-09-26 — Puente en vivo 2D (juego web) ↔ 3D (PyBullet)

**Objetivo:** que la ventana 3D del simulador refleje la partida real que se está
jugando en la interfaz web, sin intervención manual más allá de un botón.

**Primera versión — script standalone.**
`backend/servicios/simulacion/ver_partida_en_vivo.py`, ejecutable como
`python -m backend.servicios.simulacion.ver_partida_en_vivo <partida_id> <token>`.
Sondea el backend cada 1 segundo (solo `urllib.request` + `json`, sin agregar
`requests` como dependencia nueva), detecta el cierre de la ventana vía
`p.isConnected()`, maneja `KeyboardInterrupt`, y siempre limpia la escena
(`cerrar_escena`) en un `finally`. Requería que el usuario consiguiera el token JWT
a mano y lo pasara como argumento — funcional pero incómodo.

**Segunda versión — botón directo en la interfaz web.** Por pedido explícito (no
tiene sentido hacer que el usuario copie tokens a mano cuando la sesión ya está
autenticada en el navegador):
- Endpoint nuevo `POST /simulacion/abrir-ventana-3d`
  (`backend/rutas/ruta_simulacion.py` + `backend/esquemas/simulacion_esquema.py` +
  `backend/servicios/partida/servicio_simulacion_3d.py`).
- El servicio valida que la partida exista (`KeyError` → 404 si no), valida que el
  intérprete de Python del entorno conda `ajedrez` exista en disco
  (`FileNotFoundError` → 503 si no — configurable vía la variable de entorno
  `AJEDREZ_PYTHON_SIMULACION`, default
  `C:\Users\USUARIO\miniconda3\envs\ajedrez\python.exe`), y lanza
  `ver_partida_en_vivo.py` como un `subprocess.Popen` **detached** (no `run`, para no
  bloquear el request HTTP mientras la ventana 3D queda abierta).
- El token se reenvía tal cual al proceso hijo (reutilizando la dependencia
  `get_current_user` para autenticar el request HTTP normal, más una dependencia
  cruda `HTTPAuthorizationCredentials` para poder extraer el bearer token literal y
  pasárselo al hijo, que necesita autenticarse por su cuenta contra
  `GET /partida/{id}`).
- Botón "ABRIR SIMULACIÓN 3D" agregado en `SalaControl.jsx`, dentro del panel
  "BRAZO ROBÓTICO" (deshabilitado si no hay partida activa, muestra "ABRIENDO…"
  mientras carga, toast de éxito que se autolimpia a los 6 s).

**Bug encontrado y corregido: falso "partida no encontrada".** El botón fallaba con
un 404 que parecía un problema de datos (la partida "no existía" según el frontend),
pero la misma llamada por `curl` funcionaba perfecto. Causa real: tanto
`frontend/vite.config.ts` (proxy de desarrollo de Vite) como `nginx.conf`
(proxy de producción) tenían mapeados los prefijos de ruta del backend a mano, y a
ninguno de los dos se le había agregado `/simulacion` — Vite devolvía su propio 404
genérico, que la app interpretaba como si el backend hubiera dicho "no existe la
partida". De paso se encontró y corrigió el mismo problema, preexistente y no
relacionado, para el prefijo `/aprendizaje` en `nginx.conf`. Lección: cualquier
prefijo de ruta nuevo del backend hay que agregarlo en AMBOS lugares, no alcanza con
uno solo.

---

## 2026-09-26 — Entorno: Miniconda + PyBullet en Windows

`pybullet` no tiene wheel precompilado para pip en Python 3.12/Windows (pide Visual
Studio Build Tools para compilar desde código fuente) — se optó por Miniconda +
conda-forge, que sí trae binario prearmado.

- Instalación silenciosa de Miniconda vía Git Bash: los flags del instalador
  (`/InstallationType=...` etc.) son de estilo Windows, y MSYS los interpretaba como
  paths POSIX y los corrompía — se resolvió anteponiendo `MSYS_NO_PATHCONV=1` al
  comando.
- `conda env create` fallaba con `CondaToSNonInteractiveError` para los canales
  `pkgs/main`, `pkgs/r` y `pkgs/msys2` — se resolvió aceptando los términos de cada
  uno explícitamente con `conda tos accept --override-channels --channel <url>`
  antes de crear el entorno.
- Se creó el entorno `ajedrez` (conda) con `pybullet` instalado desde conda-forge.

**Dos pines de versión corregidos (con verificación directa, no de memoria):**
- `environment.yml`: se había puesto `pybullet=3.2.7` pensando que `3.25` era un
  typo — error mío, revertido tras confirmar con `conda search -c conda-forge
  pybullet` que `3.25` es una versión real de conda-forge (con numeración distinta a
  PyPI). Quedó `pybullet=3.25`.
- `requirements.txt`: tenía `python-chess==1.999.0`, que no es instalable — ese
  nombre de paquete en PyPI no tiene esa versión real. El paquete correcto,
  verificado contra la API JSON de PyPI (`https://pypi.org/pypi/chess/json`), es
  otro nombre de distribución: `chess==1.11.2`. Corregido.

---

## 2026-09-26 — Cambio de alcance: brazo real confirmado (Dobot CR5AS)

La universidad (FICCT) consiguió un brazo colaborativo real **Dobot CR5AS** (no el
kit genérico con ESP32 que estaba contemplado originalmente en el plan de 3
semanas), con software propio **DobotStudio**. El usuario compartió un video del
brazo en la universidad y una ficha técnica (PDF de DIDACTECH).

> Nota de proceso: esto toca directamente la Regla 3 de `CLAUDE.md` ("no tocar el
> brazo físico real todavía... es una fase posterior, fuera de este plan de 3
> semanas"). Se marcó explícitamente esa tensión antes de avanzar y se pidió
> confirmación; el usuario confirmó que quiere investigar y preparar la integración
> ya, dado que el brazo llegó antes de lo previsto. Hasta la fecha de esta entrada
> **no se escribió ningún código que hable con el hardware real** — solo
> investigación de protocolo/SDK, documentada abajo.

**Protocolo real investigado (confirmado contra la fuente oficial, no por
memoria):**
- Comunicación por TCP/IP en dos puertos: **29999** (dashboard — comandos como
  `EnableRobot`, `MovJ`, `MovL`, etc.) y **30004** (feedback en tiempo real).
- SDK oficial: repositorio de GitHub `Dobot-Arm/TCP-IP-Python-V4` (clases
  `DobotApi`, `DobotApiDashboard`, `DobotApiFeedBack`). Se descartó un repositorio
  con nombre parecido (`TCP-IP-Protocol-4AXis`, resuelto vía la API de GitHub tras
  un rename) por ser de la línea de producto equivocada (SCARA de 4 ejes, no el CR
  de 6 ejes que tiene la universidad).
- Requiere activar el modo "TCP/IP" una vez desde DobotStudio Pro (por defecto el
  robot se controla solo desde la propia interfaz de DobotStudio).
- Requiere que la máquina que corre el backend y el robot estén en la misma
  subred/red local.

**Plan inmediato:** instalar DobotStudio y probar la conexión física en la
universidad. Antes de eso, terminar de armar y probar bien la plataforma completa
2D↔3D (piezas + sincronización + botón, todo lo de arriba) para que cuando se
conecte el brazo real solo quede enchufar el ejecutor, no seguir armando el resto
del sistema en paralelo.

**Explícitamente NO empezado todavía (para no confundir con HU1, que sí está
terminado):**
- `EjecutorReal` (la clase que traduciría jugadas de ajedrez a comandos TCP/IP reales
  al Dobot) — no existe ni un esqueleto todavía.
- Cinemática inversa real para el Dobot — no iniciado.
- Pick-and-place guiado por visión para el brazo físico (HU9 propiamente dicho) — es
  un problema distinto al reconocimiento de tablero por foto de HU1, que ya está
  resuelto; HU9 sigue pendiente en su totalidad del lado de hardware real.

---

## 2026-09-26 — Esqueleto de `EjecutorReal` + calibración por interpolación afín

**Contexto:** antes de la prueba de conexión física en la universidad (Dobot CR5AS),
se armó todo el código que no depende de medir nada en el sitio, siguiendo el mismo
patrón Strategy/Factory que ya usa `estrategia_jugada.py` — así que el día de la
prueba alcanza con cargar números medidos, no con seguir programando ahí mismo.

**`backend/servicios/brazo/` (carpeta nueva):**
- `ejecutor_movimiento.py`: interfaz `EjecutorMovimiento` (`ejecutar_movimiento(origen,
  destino, captura)`), `EjecutorSimulado` (envuelve el PyBullet de `escena.py`, import
  diferido para no romper para quien no tenga `pybullet`) y `EjecutorReal` (TCP/IP a
  mano con el módulo estándar `socket`, sin sumar el SDK oficial como dependencia
  nueva).
- `fabrica_ejecutores.py`: `crear_ejecutor_movimiento("simulado" | "real", **kwargs)`.
- `calibracion_tablero.py`: `PuntoCalibracion` (casilla + x/y/z medidos en el robot
  real, en mm) y `calcular_posiciones_casillas(puntos)`, que resuelve una
  transformación afín 2D a partir de 3 puntos de referencia (ej. "a1", "h1", "a8") y
  devuelve las 64 casillas por interpolación, asumiendo tablero plano y casillas
  regulares. Ninguna coordenada está hardcodeada ni estimada — todo sale de los
  `PuntoCalibracion` que se midan el día de la prueba.

**`EjecutorReal.ejecutar_movimiento` — completado solo para `captura=False`.** Con
`self.posiciones_casillas` cargado, arma y envía 8 comandos por el dashboard: `MovJ`
a altura segura sobre origen, `MovL` bajando a la pieza, `DO(pin,1)` para cerrar el
efector, `MovL` subiendo, `MovJ` sobre destino, `MovL` bajando, `DO(pin,0)` para
soltar, `MovL` subiendo. Si `self.posiciones_casillas` es `None` tira `RuntimeError`
explícito (falta calibrar). Si `captura=True` tira `NotImplementedError` a propósito
— retirar la pieza capturada del tablero físico queda para la próxima vuelta, una vez
validado que el brazo se mueve bien en el caso simple.

**Dos parámetros quedan como placeholder, a confirmar en persona:**
- `altura_segura_mm=50.0` — valor de partida, no verificado contra la altura real de
  las piezas del set físico.
- `pin_efector_do=1` — todavía no se sabe si el efector cableado es gripper, ventosa
  u otro mecanismo, ni qué índice de `DO` lo controla.

**Tests:** `test_calibracion_tablero.py` verifica la reconstrucción con una grilla
sintética a mano (a1/h1/a8 separados 700mm, casillas de 100mm) contra una casilla
intermedia conocida (e5), sin hardware. `test_ejecutor_movimiento.py` cubre
`_enviar_comando` con socket mockeado, el `RuntimeError` sin calibración, el
`NotImplementedError` con `captura=True`, y la secuencia completa de 8 comandos sin
captura (también con socket mockeado) — nada de esto toca red real.

### Checklist para la prueba del lunes en la universidad

1. Confirmar que DobotStudio Pro tiene activado el modo TCP/IP (una sola vez, si no
   se hizo ya).
2. Confirmar que la máquina que corre el backend está en la misma subred que el
   Dobot.
3. En DobotStudio, jogear el brazo manualmente a las 3 casillas de referencia (ej.
   a1, h1, a8) y anotar su X/Y/Z reportados — esos son los `PuntoCalibracion` reales.
4. Jogear también a una altura de contacto real sobre una pieza (el `z` de
   calibración) y a la altura segura deseada, para fijar `altura_segura_mm` con un
   valor verificado en vez del placeholder de 50.0.
5. Confirmar con quien armó/cableó el brazo qué mecanismo de sujeción tiene (gripper,
   ventosa, etc.) y qué índice de `DO` lo controla — reemplaza el `pin_efector_do=1`
   puesto como placeholder.
6. Instanciar `EjecutorReal(host=..., posiciones_casillas=calcular_posiciones_casillas([...]),
   altura_segura_mm=..., pin_efector_do=...)`, llamar `conectar()`, y probar UN
   movimiento simple sin captura antes de nada más.
7. Nota explícita: la lógica de captura (retirar la pieza de `destino` del tablero
   físico) todavía no está implementada — es el siguiente paso una vez validado el
   movimiento básico.
