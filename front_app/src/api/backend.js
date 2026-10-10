// Copia de frontend/src/api/backend.js (ver PLAN_FRONT_APP.md §2.3). Los cambios de contrato se aplican en ambos.
/**
 * Capa de comunicación con el backend real (FastAPI). Solo fetch — sin
 * estado ni JSX. Nada de datos simulados: si el backend no responde, el
 * error se propaga tal cual para que la interfaz lo muestre.
 * Incluye automáticamente el token JWT si existe en localStorage.
 */

async function solicitar(endpoint, opciones = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json", ...opciones.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch(endpoint, {
    method: "POST",
    headers,
    ...opciones,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status; // permite a la UI distinguir 404 de 503, etc.
    throw error;
  }
  return respuesta.json();
}

export function crearPartida(nivel, fenInicial, tipoOponente = "modelo") {
  const cuerpo = {
    nivel,
    tipo_oponente: tipoOponente,
  };
  if (fenInicial) cuerpo.fen_inicial = fenInicial;
  return solicitar("/partida", { body: JSON.stringify(cuerpo) });
}

export function obtenerPartida(partidaId) {
  return solicitar(`/partida/${partidaId}`, { method: "GET" });
}

/**
 * Análisis jugada por jugada de una partida con la red propia (solo facilitador):
 * qué elegiría la red en cada posición frente a lo que se jugó. No usa Stockfish.
 */
export function analisisRedPartida(partidaId) {
  return solicitarAuth(`/partida/${partidaId}/analisis-red`);
}

/**
 * Arma el `Error` de una respuesta HTTP fallida: usa el `detail` del backend
 * solo si es texto (un 422 de FastAPI manda una lista, que no sirve mostrar
 * tal cual) y conserva el `status` para que la UI distinga 404, 409, 403, etc.
 */
async function errorDeRespuesta(respuesta) {
  const detalle = await respuesta.json().catch(() => null);
  const mensaje = typeof detalle?.detail === "string" ? detalle.detail : `Error ${respuesta.status}`;
  const error = new Error(mensaje);
  error.status = respuesta.status;
  return error;
}

/**
 * Partida sin terminar del usuario autenticado, para ofrecer retomarla en vez
 * de crear otra al abrir la Sala de Control. Devuelve `null` si no hay ninguna
 * (el backend responde `null` o 204). Campos nuevos opcionales: `estado`,
 * `iniciada_en`, `actualizada_en`, `jugadas_jugador`. Si el endpoint todavía no
 * existe en el backend desplegado lanza el error con su `status` (404/405): quien
 * llama decide degradar al flujo de siempre.
 */
export async function obtenerPartidaEnCurso() {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/partida/en-curso", { method: "GET", headers });
  if (respuesta.status === 204) return null;
  if (!respuesta.ok) throw await errorDeRespuesta(respuesta);
  const datos = await respuesta.json().catch(() => null);
  return datos && typeof datos === "object" ? datos : null;
}

/** Registro de partidas jugadas mientras el backend sigue corriendo (no sobrevive un reinicio). */
export function listarPartidas() {
  return solicitar("/partida", { method: "GET" });
}

export function moverPartida(partidaId, jugada) {
  return solicitar(`/partida/${partidaId}/mover`, {
    body: JSON.stringify({ jugada }),
  });
}

/** Detecta la jugada hecha en el tablero físico (cámara fija) y la aplica (RF11). */
export function moverPartidaDesdeFoto(partidaId) {
  return solicitar(`/partida/${partidaId}/mover-desde-foto`);
}

/** Casillas destino legales para la pieza parada en `casilla`, para resaltarlas al seleccionarla. */
export function obtenerJugadasLegales(partidaId, casilla) {
  return solicitar(`/partida/${partidaId}/jugadas-legales?casilla=${casilla}`, {
    method: "GET",
  });
}

/**
 * Análisis jugada por jugada de una partida ya jugada, para la vista de
 * Aprendizaje y el Panel de Aprendizaje (tutor Turing). `rango` es opcional
 * ("Principiante" | "Intermedio" | "Avanzado") — el backend todavía no lo
 * lee (ver HU5/HU6, retroalimentación adaptada al nivel, en curso), pero ya
 * se manda: en cuanto el backend lo soporte, la retroalimentación se ajusta
 * sola sin tocar este archivo.
 */
export function analisisCompletoPartida(partidaId, rango) {
  const query = rango ? `?rango=${encodeURIComponent(rango)}` : "";
  return solicitar(`/partida/${partidaId}/analisis-completo${query}`, {
    method: "GET",
  });
}

/**
 * Lanza la ventana nativa de PyBullet en la máquina del backend, sincronizada
 * en vivo con la partida indicada — evita tener que correr `ver_partida_en_vivo.py`
 * a mano con un token copiado del navegador.
 */
export function abrirSimulacion3D(partidaId) {
  return solicitar("/simulacion/abrir-ventana-3d", {
    body: JSON.stringify({ partida_id: partidaId }),
  });
}

/**
 * Prende/apaga, por partida, si el jugador puede ver la simulación 3D, usar
 * la cámara del tablero físico, y/o si la partida se transmite en vivo a los
 * jugadores (`permite_simulacion_3d`, `permite_camara`, `es_demostracion`).
 * Edición parcial — solo facilitadores, y `es_demostracion` solo se puede
 * prender en una partida propia del facilitador (400 si no lo es). Todos los
 * parámetros son opcionales.
 */
export function actualizarPermisosPartida(partidaId, permisos) {
  return solicitar(`/partida/${partidaId}/permisos`, {
    method: "PATCH",
    body: JSON.stringify(permisos),
  });
}

/**
 * Partida que el facilitador marcó como demostración en vivo (`es_demostracion`),
 * si hay alguna — cualquier usuario autenticado puede consultarla, para poder
 * avisarle al jugador que hay una transmisión activa. Devuelve `null` si no hay
 * ninguna. El contrato exacto de "no hay ninguna" todavía puede cambiar del
 * lado del backend (204, 404, o un cuerpo vacío/`{activa: false}`), así que se
 * cubren los casos más probables en vez de asumir uno solo.
 */
export async function obtenerDemostracionActiva() {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/partida/demostracion-activa", { method: "GET", headers });
  if (respuesta.status === 204 || respuesta.status === 404) {
    return null;
  }
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  const datos = await respuesta.json().catch(() => null);
  if (!datos || datos.activa === false) return null;
  return datos;
}

export function calcularJugada(fen, nivel) {
  return solicitar("/jugada", { body: JSON.stringify({ fen, nivel }) });
}

export function analizarPosicion(fen, nivel) {
  return solicitar("/analisis", { body: JSON.stringify({ fen, nivel }) });
}

/**
 * Reconoce el tablero. Si se pasa `archivoFoto` (una imagen ya sacada, ej.
 * de la galería del celular), la usa en vez de sacar una foto nueva de la
 * cámara fija — útil para no depender de que la cámara en vivo acierte el
 * encuadre justo en el momento de mostrar el sistema.
 */
export async function reconocerTablero(turno = "w", archivoFoto = null) {
  const token = localStorage.getItem("access_token");
  const datos = new FormData();
  datos.append("turno", turno);
  if (archivoFoto) {
    datos.append("foto_subida", archivoFoto);
  }
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/vision/reconocer", {
    method: "POST",
    body: datos,
    headers,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  return respuesta.json();
}

/**
 * Captura una foto de la cámara fija. Va con fetch y el token porque un
 * <img src> no manda el header Authorization y la ruta exige sesión. Devuelve
 * un object URL (JPEG), listo para un <img src>; quien lo use es responsable
 * de revocarlo con `URL.revokeObjectURL` cuando ya no haga falta.
 */
export async function obtenerUrlFotoCamara() {
  const token = localStorage.getItem("access_token");
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/vision/foto", { headers, cache: "no-store" });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  const blob = await respuesta.blob();
  return URL.createObjectURL(blob);
}

/**
 * Pide al backend la foto subida enderezada con la grilla 8x8 dibujada
 * encima — prueba visual de que la detección geométrica del tablero
 * encontró las esquinas y alineó bien, sin depender del clasificador de
 * piezas. Devuelve un object URL (JPEG), listo para un <img src=...>; quien
 * lo use es responsable de revocarlo con `URL.revokeObjectURL` cuando ya no
 * haga falta.
 */
export async function obtenerUrlGrillaDebug(archivoFoto) {
  const token = localStorage.getItem("access_token");
  const datos = new FormData();
  datos.append("foto_subida", archivoFoto);
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/vision/grilla-debug", {
    method: "POST",
    body: datos,
    headers,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  const blob = await respuesta.blob();
  return URL.createObjectURL(blob);
}

/** Health check del backend — sin auth para que funcione antes de login */
export async function backendEnLinea() {
  try {
    const respuesta = await fetch("/health");
    return respuesta.ok;
  } catch {
    return false;
  }
}

/** Autenticación tradicional */
export async function login(email, password, rolEsperado) {
  const respuesta = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, rol_esperado: rolEsperado }),
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  return respuesta.json();
}

/** Autenticación con Google OAuth (ID Token / Credential) */
export async function loginGoogle(credential, rolSeleccionado = "jugador", claveFacilitador = null) {
  const respuesta = await fetch("/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      credential,
      rol_seleccionado: rolSeleccionado,
      clave_facilitador: claveFacilitador,
    }),
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  return respuesta.json();
}

/** Registro de nueva cuenta */
export async function registro(email, nombre, password, rol = "jugador", claveFacilitador = null) {
  const respuesta = await fetch("/auth/registro", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      nombre,
      password,
      rol,
      clave_facilitador: claveFacilitador,
    }),
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  return respuesta.json();
}

/** Estado del modelo de aprendizaje (disponible, dispositivo, checkpoint, etc.) */
export function estadoModelo() {
  return solicitar("/aprendizaje/estado-modelo", { method: "GET" });
}

/** Inferencia del modelo propio: candidatas, saliencia, etc. */
export function inferenciaModelo(fen) {
  return solicitar("/aprendizaje/inferencia", {
    body: JSON.stringify({ fen }),
  });
}

async function solicitarAuth(endpoint, opciones = {}) {
  const token = localStorage.getItem("access_token");
  const respuesta = await fetch(endpoint, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...opciones.headers,
    },
    ...opciones,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  return respuesta.json();
}

/**
 * Perfil actual del usuario autenticado, leído del servidor. El `usuario` que
 * la web guarda en localStorage al loguear no se actualiza solo: esto sirve
 * para traer el nivel recalibrado (`nivel_estimado`, `rango_estimado`) y los
 * campos `diagnostico_completado` / `partidas_calibradas`.
 */
export function obtenerPerfil() {
  return solicitarAuth("/auth/me");
}

/**
 * Calibra el nivel del jugador con una partida terminada: el backend la
 * analiza contra Stockfish (tarda unos segundos) y devuelve si quedó
 * registrada (`registrada`), el motivo si no (`motivo`), la precisión y el
 * nivel/rango nuevo. Es idempotente: repetirla para la misma partida responde
 * `motivo: "ya_registrada"`.
 */
export function calibrarPartida(partidaId) {
  return solicitarAuth(`/partida/${partidaId}/calibrar`, { method: "POST" });
}

/**
 * Nivel medido del jugador para la sección "Tu nivel": nivel/rango, progreso
 * hacia el siguiente nivel, últimas calibraciones y la escala vigente.
 */
export function obtenerNivelJugador() {
  return solicitarAuth("/auth/nivel");
}

/**
 * Edición del propio perfil — cualquier rol autenticado (RF/HU perfil).
 * Edición parcial: solo se pisan los campos incluidos en `datos`.
 */
export function actualizarPerfil(datos) {
  return solicitarAuth("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(datos),
  });
}

/**
 * Guarda el nivel/rango que el jugador elige a mano en Mi Perfil. Mismo
 * endpoint que ya usa el diagnóstico "Mide tu nivel" de la app móvil
 * (`PATCH /auth/nivel-estimado`, ver game_screen.dart) — acá no hay
 * diagnóstico, es autoselección directa, así que se reusan los mismos pares
 * nivel/rango que ya define la app móvil para que ambas plataformas hablen
 * el mismo idioma (Avanzado→18, Intermedio→11, Principiante→5). El backend
 * puede recalibrar este valor más adelante solo, analizando partidas reales
 * — esto solo pisa el punto de partida.
 */
export function guardarNivelEstimado(nivel, rango) {
  return solicitarAuth("/auth/nivel-estimado", {
    method: "PATCH",
    body: JSON.stringify({ nivel, rango }),
  });
}

/**
 * Sube (o reemplaza) la foto de perfil real del usuario autenticado — multipart,
 * mismo patrón que `subirVideoPieza`. Devuelve el `UsuarioResponse` actualizado
 * (con la nueva `avatar_url`). Pedido a backend-fastapi (`POST /auth/foto`),
 * puede no estar listo todavía — si no existe, la UI lo trata igual que
 * cualquier otro endpoint en construcción (404/405).
 */
export async function subirFotoPerfil(archivo) {
  const token = localStorage.getItem("access_token");
  const datos = new FormData();
  datos.append("archivo", archivo);
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/auth/foto", {
    method: "POST",
    body: datos,
    headers,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  return respuesta.json();
}

/** Gestión de usuarios (solo facilitadores) */

export function listarUsuarios() {
  return solicitarAuth("/auth/usuarios");
}

export function historialPartidasUsuario(usuarioId, limit = 10, offset = 0) {
  return solicitarAuth(
    `/auth/usuarios/${usuarioId}/historial-partidas?limit=${limit}&offset=${offset}`,
  );
}

/**
 * Historial de partidas del usuario logueado (cualquier rol, no solo
 * facilitador) — para el Panel de Aprendizaje del jugador ("Repaso de tu
 * partida", insignia "Primera partida jugada"). Ya existía en el backend
 * para HU14 (`backend/rutas/ruta_usuario.py`) aunque hasta ahora ningún
 * componente del frontend lo consumía — no hizo falta pedir un endpoint
 * nuevo.
 */
export function historialPartidasPropio(limit = 10, offset = 0) {
  return solicitarAuth(`/usuario/historial-partidas?limit=${limit}&offset=${offset}`);
}

/**
 * Videos por pieza que el facilitador autenticado ya subió — Configuración
 * de Enseñanza. Dict `tipo_pieza -> url`; una pieza ausente significa que
 * se usa el video por defecto del sistema, no que hubo un error.
 */
export function obtenerVideosFacilitador() {
  return solicitarAuth("/facilitador/videos");
}

/**
 * Sube (o reemplaza) el video educativo del facilitador para `tipoPieza`
 * ("rey" | "dama" | "torre" | "alfil" | "caballo" | "peon"). Multipart
 * aparte de `solicitar`/`solicitarAuth`: el content-type con boundary lo
 * arma el navegador solo al mandar un `FormData`, así que acá no se fija
 * "Content-Type" a mano (ver `reconocerTablero` más arriba, mismo patrón).
 * Devuelve `{tipo_pieza, url}`.
 */
export async function subirVideoPieza(tipoPieza, archivo) {
  const token = localStorage.getItem("access_token");
  const datos = new FormData();
  datos.append("archivo", archivo);
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch(`/facilitador/videos/${tipoPieza}`, {
    method: "POST",
    body: datos,
    headers,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  return respuesta.json();
}

/** Tutor conversacional "Turing" (Panel de Aprendizaje) */

/**
 * Manda un mensaje al tutor conversacional "Turing" y persiste el turno en
 * el backend — misma conversación que lee `obtenerHistorialTutor`. Devuelve
 * `{respuesta, creado_en}`. El backend responde 503 si el tutor no está
 * disponible (LLM caído o sin API key configurada) — la UI distingue ese
 * caso vía `error.status` para mostrar un aviso amigable en vez de un error
 * crudo.
 */
export function enviarMensajeTutor(mensaje) {
  return solicitarAuth("/tutor/mensaje", {
    method: "POST",
    body: JSON.stringify({ mensaje }),
  });
}

/**
 * Historial de la conversación con Turing del usuario logueado, en orden
 * cronológico (el más viejo primero). `limite` es la cantidad de turnos a
 * traer (cada mensaje del usuario y cada respuesta cuentan como un turno
 * cada uno), no de intercambios completos.
 */
export function obtenerHistorialTutor(limite = 50) {
  return solicitarAuth(`/tutor/historial?limite=${limite}`);
}

/**
 * Borra el historial de conversación con Turing del usuario logueado
 * (reinicia la memoria del tutor — útil si una demo se traba a mitad de
 * conversación). Devuelve 204 sin cuerpo, así que no reusa
 * `solicitar`/`solicitarAuth` (que siempre parsean JSON de la respuesta):
 * arma el fetch a mano, con el mismo manejo de token y de errores que el
 * resto del archivo (ver `obtenerDemostracionActiva` más arriba, mismo
 * criterio defensivo).
 */
export async function borrarHistorialTutor() {
  const token = localStorage.getItem("access_token");
  const respuesta = await fetch("/tutor/historial", {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
}

/** Entrenamiento del modelo Turing (solo facilitadores) */

/**
 * Estado de los datos acumulados para reentrenar a Turing: umbral de partidas,
 * cuántas partidas válidas hay en total y cuántas son nuevas desde la última
 * descarga, progreso (0..1), si ya está `listo_para_entrenar`, la
 * `ultima_descarga` (o `null`) y el `modelo_actual`. Responde 403 a los
 * jugadores. El reentrenamiento en sí NO es automático: lo hace el equipo
 * técnico por lotes (HU4, pendiente); esto solo dice si ya hay datos suficientes.
 */
export function obtenerEstadoEntrenamiento() {
  return solicitarAuth("/entrenamiento/estado");
}

/** Cómo juega Turing según el nivel de la partida, frente a Stockfish (solo facilitador). */
export function obtenerTuringPorNivel() {
  return solicitarAuth("/entrenamiento/turing-por-nivel");
}

/**
 * Nombre de archivo que viene en el header `Content-Disposition`
 * (`filename="..."` o `filename*=UTF-8''...`), o `null` si no se puede leer.
 */
function nombreDesdeContentDisposition(cabecera) {
  if (!cabecera) return null;
  const codificado = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/.exec(cabecera);
  if (codificado) {
    try {
      return decodeURIComponent(codificado[1].trim());
    } catch {
      // si la codificación viene rota se prueba con el formato simple
    }
  }
  const simple = /filename\s*=\s*"?([^";]+)"?/.exec(cabecera);
  return simple ? simple[1].trim() : null;
}

/** `dataset_ajedrez_AAAAMMDD_HHMM.zip` con la hora local, por si el header no se puede leer. */
function nombreDatasetPorDefecto() {
  const ahora = new Date();
  const dos = (n) => String(n).padStart(2, "0");
  const fecha = `${ahora.getFullYear()}${dos(ahora.getMonth() + 1)}${dos(ahora.getDate())}`;
  const hora = `${dos(ahora.getHours())}${dos(ahora.getMinutes())}`;
  return `dataset_ajedrez_${fecha}_${hora}.zip`;
}

/**
 * Descarga el dataset de entrenamiento (ZIP con partidas.pgn, jugadas.csv,
 * partidas.csv, manifiesto.json y LEEME.txt). Hace falta leer el binario con
 * fetch (lleva el token), así que devuelve `{ blob, nombre }` y la pantalla
 * dispara la descarga con un `<a download>`. Con `soloNuevas` trae únicamente
 * las partidas posteriores a la última descarga. Si falla lanza un `Error` con
 * el `detail` del backend (ej. 409 cuando todavía no hay partidas válidas).
 */
export async function descargarDatasetEntrenamiento({ soloNuevas = false } = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const respuesta = await fetch("/entrenamiento/dataset", {
    method: "POST",
    headers,
    body: JSON.stringify({ solo_nuevas: Boolean(soloNuevas) }),
  });
  if (!respuesta.ok) throw await errorDeRespuesta(respuesta);
  const blob = await respuesta.blob();
  const nombre =
    nombreDesdeContentDisposition(respuesta.headers.get("Content-Disposition")) ?? nombreDatasetPorDefecto();
  return { blob, nombre };
}
