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

---

## 2026-09-27 — Investigación profunda del protocolo y especificaciones (Dobot CR5AS)

**Contexto:** el PDF que compartió DIDACTECH (`Aplicaciones_DOBOT_CR5AS_Vision_Artificial`)
es material comercial — 9 páginas listando casos de uso posibles (pick and place,
bin picking, clasificación, etc.) y una tabla de perfil funcional muy general. No
tiene contenido técnico de protocolo ni de SDK. Se pidió investigar más a fondo el
brazo en sí; lo de abajo sale de la documentación oficial de Dobot y de terceros
(Trossen Robotics, que republica la documentación técnica completa de la serie CR),
no del PDF comercial.

**Especificaciones confirmadas (contra ficha oficial, no contra el PDF de
DIDACTECH):**
- 6 ejes, carga útil 5 kg, alcance máximo declarado 900 mm (RBTX/QVIRO) — Trossen
  reporta 1096 mm de alcance máximo con 1534 mm de espacio de trabajo recomendado;
  hay discrepancia entre fuentes comerciales y la doc técnica, a confirmar con la
  ficha física del equipo de la universidad antes de diseñar el layout del tablero.
- Repetibilidad ±0,02 mm, peso del brazo ~23–25 kg, velocidad máx. ~2 m/s, rango de
  temperatura de operación 0–50 °C.
- Controlador Dobot CC161: 16 entradas digitales + 16 E/S digitales multiplexadas,
  2 salidas analógicas + 2 entradas analógicas (0–10V o 4–20mA), 1 entrada de
  encoder incremental ABZ. Soporta EtherCAT, Ethernet, Modbus, TCP/IP, EtherNet/IP
  y ROS.
- 22 funciones de seguridad incorporadas (relevante para el checklist de seguridad
  de la Sección 6 del CLAUDE.md del proyecto — uso en ambiente universitario con
  estudiantes alrededor).

**Protocolo TCP/IP — más detalle sobre lo ya documentado el 26/09:**
- Puerto 29999 (dashboard) exige **antes que nada** activar el modo TCP en
  DobotStudio Pro — si no, cualquier comando responde literalmente
  `"Control Mode Is Not Tcp"`. Ya lo teníamos anotado; se confirma que es el error
  más común reportado por otros usuarios del SDK.
- Secuencia de arranque correcta (según doc oficial): `PowerOn()` → esperar ~10 s →
  `ClearError()` → `EnableRobot(peso, cx, cy, cz)` (acepta parámetros de carga del
  efector) → `User(index)` / `Tool(index)` para fijar el sistema de coordenadas →
  recién ahí `MovJ`/`MovL`. `EjecutorReal.conectar()` hoy no llama `PowerOn()` ni
  `ClearError()` — pendiente revisar si el robot de la universidad ya queda
  energizado por otro medio (interruptor físico) o si hace falta agregar esos dos
  pasos al esqueleto antes de la prueba.
- Formato de respuesta confirmado: `"ErrorID,{valores},Comando(...);"`. `ErrorID=0`
  es éxito; `-10000` comando no encontrado; `-20000` cantidad de parámetros
  incorrecta. `_enviar_comando` en `ejecutor_movimiento.py` debería parsear el
  `ErrorID` en vez de solo revisar que la conexión no tirara excepción — pendiente.
- **Hallazgo importante para el checklist:** el robot resuelve la cinemática
  inversa internamente para `MovJ`/`MovL` (reciben pose cartesiana `X,Y,Z,Rx,Ry,Rz`
  y el propio controlador calcula los ángulos de junta). Existe además un comando
  de dashboard `InverseSolution(...)` para resolver IK manualmente si hiciera
  falta verificar una pose antes de moverse. Esto quiere decir que el ítem
  "cinemática inversa real para el Dobot — no iniciado" probablemente **no haga
  falta implementarlo a mano**: alcanza con enviar la pose cartesiana calibrada
  (que ya resuelve `calibracion_tablero.py`) y dejar que el propio Dobot resuelva
  la IK. Falta validarlo en la prueba física, pero cambia el alcance pendiente de
  HU9.
- Puerto 30004 (feedback en tiempo real): paquetes de 1440 bytes cada 8 ms — no
  usado todavía por `EjecutorReal`, que hoy solo habla por 29999. Suficiente para
  el caso simple (comandos síncronos, esperar respuesta), se necesitaría solo si
  más adelante se quiere telemetría en vivo o detección de colisión en tiempo real
  desde el backend.
- Comandos de seguridad relevantes que no estaban contemplados en el esqueleto:
  `SetCollisionLevel(0-5)` y `SetSafeSkin(status)` (si el equipo de la universidad
  tiene piel sensible instalada). Candidatos a llamar una vez en `conectar()`,
  antes de la primera prueba.

**Efector final para piezas de ajedrez — pendiente de confirmar en persona.** La
serie de gripper adaptable AG de Dobot (diseño tipo linkage) está pensada para
objetos redondos/esféricos, lo que calza mejor con piezas de ajedrez torneadas
(especialmente el rey y la reina, de base angosta y cuerpo curvo) que una pinza
paralela genérica. Sigue sin saberse qué efector está cableado físicamente en el
brazo de la universidad — este punto del checklist original (punto 5) no cambia.

**Fuentes consultadas:**
- [DOBOT CR5A — Unchained Robotics](https://unchainedrobotics.de/en/products/robot/cobot/dobot-cr5a)
- [DOBOT CR5 Specifications — QVIRO](https://qviro.com/product/cr5/specifications)
- [Specifications — Dobot CR-Series Documentation (Trossen Robotics)](https://docs.trossenrobotics.com/dobot_cr_cobots_docs/specifications.html)
- [Protocol Definition — Dobot CR-Series Documentation (Trossen Robotics)](https://docs.trossenrobotics.com/dobot_cr_cobots_docs/tcpip_protocol/functions.html)
- [Which network communication ports are available on the CR series? — Dobot FAQ](https://www.dobot-robots.com/service/faq/459.html)
- [Dobot-Arm/TCP-IP-Python-V4 — GitHub](https://github.com/Dobot-Arm/TCP-IP-Python-V4)
- [Wide Applications of DOBOT CR5 Collaborative Robot — Dobot](https://www.dobot-robots.com/insights/news/wide-applications-of-dobot-cr5-collaborative-robot.html)

**Pendiente para la prueba física (se suma al checklist existente):**
8. Confirmar si `EjecutorReal.conectar()` necesita agregar `PowerOn()` +
   `ClearError()` antes de `EnableRobot()`, o si el robot ya llega energizado.
9. Decidir si vale la pena llamar `SetCollisionLevel` y (si aplica) `SetSafeSkin`
   como parte de `conectar()`, dado el uso en ambiente universitario.
10. Validar en la prueba real que enviar `MovL` con la pose calibrada (sin resolver
    IK a mano) mueve el brazo correctamente — si es así, se puede tachar
    definitivamente "cinemática inversa real" de los pendientes de HU9.

---

## 2026-09-27 — Wiring modelo + visión + brazo, y fix de sincronización de EjecutorSimulado/EjecutorReal

**Contexto:** el modelo propio decidiendo jugadas (HU3/HU4), la visión detectando la
jugada humana desde una foto (HU1/HU9, `mover_desde_foto`) y el ejecutor de
movimiento (`EjecutorSimulado`/`EjecutorReal`) ya funcionaban cada uno por separado,
pero nada los conectaba: `servicio_partida.mover()` nunca llamaba a un
`EjecutorMovimiento`, así que la jugada de respuesta de la estrategia activa solo se
aplicaba al `chess.Board` en memoria, nunca al brazo (ni simulado ni real).

**Bug real encontrado antes de cablear nada.** `EjecutorSimulado.__init__` creaba su
propio `self.tablero = chess.Board()` (posición estándar) y cada
`ejecutar_movimiento` hacía `self.tablero.push(...)` sobre esa copia interna. Como el
ejecutor solo debe recibir la jugada de la estrategia (nunca la del humano — esa ya
se jugó a mano sobre el tablero físico real, por eso `mover_desde_foto` puede
detectarla con la cámara), esa copia interna quedaba desincronizada de la posición
real desde la segunda jugada de la estrategia en adelante: le faltaban todas las
jugadas del humano de por medio. `piece_at` podía devolver una pieza equivocada o
`None`, y la escena PyBullet terminaba mal.

**Fix aplicado (`backend/servicios/brazo/ejecutor_movimiento.py`).** Se cambió la
interfaz de `EjecutorMovimiento.ejecutar_movimiento` de
`(origen: str, destino: str, captura: bool)` a
`(tablero_antes: chess.Board, jugada: chess.Move)`. Quien llama pasa el tablero real
inmediatamente antes de la jugada (una copia, nunca mutada) y la jugada ya resuelta
como objeto `chess.Move`; `origen`/`destino`/`captura` se derivan ahí mismo
(`chess.square_name`, `tablero_antes.is_capture(jugada)`), y la promoción ya viene
resuelta en `jugada.promotion` (python-chess la arma al parsear la jugada, ya no hace
falta forzarla a mano a dama). `EjecutorSimulado` dejó de mantener `self.tablero`
como estado acumulado: cada llamada usa `tablero_antes.copy()` + `push(jugada)` solo
para esa jugada, así no hay estado interno que se pueda desincronizar.
`EjecutorReal.ejecutar_movimiento` sigue igual en su secuencia de comandos, solo
cambia de dónde saca `origen`/`destino`/`captura`. Se actualizó
`test_ejecutor_movimiento.py` a la nueva firma y se sumó un test que reproduce el
escenario real (dos jugadas de la estrategia con jugadas del humano de por medio que
el ejecutor nunca ve) para confirmar que ya no se desincroniza.

**Wiring del flujo completo.**
- `Partida.usa_brazo: bool = False` (`backend/modelos/partida.py`) — mismo patrón que
  `permite_camara`/`permite_simulacion_3d`: togglable por partida vía
  `PATCH /partida/{id}/permisos` (solo facilitador), columna nueva en `PartidaORM`
  (`backend/modelos/tablas_orm.py`) y mapeo en `repositorio_partida.py` para que
  sobreviva con `RepositorioPartidasPostgres`, igual que los otros permisos.
- `backend/servicios/brazo/servicio_brazo.py` (nuevo): `ejecutar_respuesta_en_brazo(partida,
  tablero_antes, jugada) -> str | None`. No hace nada si `partida.usa_brazo` es
  `False`. Si está prendido, obtiene (lazy, cacheado a nivel módulo) un
  `EjecutorMovimiento` vía `crear_ejecutor_movimiento(modo, **kwargs)`, con `modo`
  desde `AJEDREZ_MODO_BRAZO` (default `"simulado"`, **nunca** `"real"` por defecto —
  regla 3 del `CLAUDE.md` del proyecto) y, si `modo="real"`, `host`/
  `puerto_dashboard` desde `AJEDREZ_BRAZO_HOST`/`AJEDREZ_BRAZO_PUERTO_DASHBOARD`.
  Cualquier excepción al ejecutar (brazo desconectado, sin calibración, captura no
  implementada, o incluso el host real sin configurar) se loguea
  (`logging.exception`, no `print`) y se devuelve como string en vez de propagarse —
  la partida digital ya está resuelta en ese punto, un fallo físico no debe romper el
  turno ni la respuesta HTTP.
- `servicio_partida.mover()`: justo después de resolver `jugada_motor_san` y antes de
  pisar `tablero_intento`, se guarda `tablero_antes_motor = tablero_intento.copy()` y
  se obtiene la jugada real con `tablero_intento.parse_san(jugada_motor_san)` (en vez
  de `push_san` directo, para tener el objeto `chess.Move`), se hace `push` de esa
  jugada, y recién ahí se llama `ejecutar_respuesta_en_brazo(partida,
  tablero_antes_motor, jugada_motor_move)`. El resultado se expone como
  `error_brazo: str | None` en el dict que devuelve `mover()` (y por lo tanto en
  `ResultadoMovimientoResponse`, `backend/esquemas/partida_esquema.py`).
  `mover_desde_foto()` no necesitó cambios: delega en `mover()`, así que hereda el
  wiring gratis (confirmado leyendo el código, no asumido).

**Tests agregados/actualizados:** `test_ejecutor_movimiento.py` (nueva firma + caso de
desincronización), `test_servicio_brazo.py` (nuevo — `usa_brazo=False` no hace nada,
`usa_brazo=True` llama al ejecutor con `tablero_antes`/`jugada` correctos, error del
ejecutor capturado como string, `modo=real` sin `AJEDREZ_BRAZO_HOST` no rompe),
`test_servicio_partida.py` (wiring: `usa_brazo=True` invoca
`ejecutar_respuesta_en_brazo` con la jugada de la estrategia — nunca la del humano —
y `error_brazo` aparece en la respuesta sin abortar la jugada digital). Toda la
suite de `backend/servicios/brazo/` y `backend/servicios/partida/` pasa en verde.

**Pendiente:** el frontend (Sala de Control) todavía no tiene el toggle de
`usa_brazo` en la UI de permisos — falta avisarle a `frontend-react` que
`EstadoPartidaResponse` y `ActualizarPermisosPartidaRequest` tienen un campo nuevo.
La ejecución de captura en `EjecutorReal` sigue sin implementar (fuera de alcance,
ya documentado arriba). Se encontró además, de paso, que correr
`python -m pytest backend/` completo en una sola invocación en el env conda
`ajedrez` de esta máquina hace segfault por una interacción de torch/OpenMP al
cargar varios checkpoints `.pt` en el mismo proceso (`backend/servicios/vision/piezas.py`
tras `backend/servicios/aprendizaje/` y/o `backend/servicios/estrategias/test_fabrica_estrategias.py`)
— no es un bug de este cableado (cada módulo pasa 100% en aislamiento), se dejó
flageado como tarea de entorno aparte.
