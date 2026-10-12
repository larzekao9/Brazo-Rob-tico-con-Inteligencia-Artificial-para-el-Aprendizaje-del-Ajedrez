// Punto central de las llamadas autenticadas (PLAN_MULTIJUGADOR.md §7.5).
// - Tokens siempre persistentes en localStorage (con try/catch: puede no haber almacenamiento).
// - Un 401 intenta refrescar UNA vez (una sola promesa en vuelo) y reintenta la petición.
// - Solo un 401/403 del propio refresh cierra la sesión: red caída, 5xx o 502/503 NO borran tokens.

const CLAVE_ACCESO = "access_token";
const CLAVE_REFRESCO = "refresh_token";

/** Mensaje único para "el backend no responde" (red caída, 5xx, proxy sin destino). */
export const MENSAJE_SIN_CONEXION = "No se pudo conectar con el servidor";

export function leerAcceso() {
  try {
    return localStorage.getItem(CLAVE_ACCESO);
  } catch {
    return null;
  }
}

function leerRefresco() {
  try {
    return localStorage.getItem(CLAVE_REFRESCO);
  } catch {
    return null;
  }
}

/** Guarda el par de tokens; si no llega un refresh nuevo conserva el anterior. */
export function guardarTokens(acceso, refresco) {
  try {
    localStorage.setItem(CLAVE_ACCESO, acceso);
    if (refresco) localStorage.setItem(CLAVE_REFRESCO, refresco);
  } catch {
    /* sin almacenamiento: la sesión dura solo mientras la pestaña esté abierta */
  }
}

export function borrarTokens() {
  try {
    localStorage.removeItem(CLAVE_ACCESO);
    localStorage.removeItem(CLAVE_REFRESCO);
  } catch {
    /* nada que borrar */
  }
}

export function hayTokens() {
  return leerAcceso() !== null;
}

function errorSinConexion() {
  const error = new Error(MENSAJE_SIN_CONEXION);
  error.sinConexion = true;
  return error;
}

/** `fetch` que traduce un fallo de red al error legible (sin tocar los abortos). */
async function fetchRed(url, init) {
  try {
    return await fetch(url, init);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw errorSinConexion();
  }
}

/**
 * Arma el `Error` de una respuesta HTTP fallida: usa el `detail` solo si es texto (un 422 trae
 * una lista), conserva `status` y convierte los 5xx en "No se pudo conectar con el servidor".
 */
export async function errorDeRespuesta(respuesta) {
  if (respuesta.status >= 500) {
    const error = errorSinConexion();
    error.status = respuesta.status;
    return error;
  }
  const detalle = await respuesta.json().catch(() => null);
  const error = new Error(typeof detalle?.detail === "string" ? detalle.detail : `Error ${respuesta.status}`);
  error.status = respuesta.status;
  return error;
}

// --- Aviso de cierre de sesión forzado (lo escucha SesionContext) ---
const oyentes = new Set();

/** Suscribe una función que se llama cuando la sesión se pierde a mitad de uso. Devuelve la baja. */
export function alPerderSesion(oyente) {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}

function perderSesion() {
  borrarTokens();
  oyentes.forEach((oyente) => oyente());
}

// --- Refresh con una sola promesa en vuelo ---
let refrescoEnVuelo = null;

async function pedirRefresco() {
  const refresco = leerRefresco();
  if (!refresco) return null;
  const respuesta = await fetchRed("/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresco }),
  });
  if (respuesta.status >= 500) throw errorSinConexion();
  if (!respuesta.ok) return null; // 401/403/4xx: el refresh ya no sirve
  const datos = await respuesta.json().catch(() => null);
  if (!datos?.access_token) return null;
  guardarTokens(datos.access_token, datos.refresh_token);
  return datos.access_token;
}

/** Access token nuevo, `null` si el refresh no sirve; lanza (sinConexion) si el backend no responde. */
export function refrescarSesion() {
  if (!refrescoEnVuelo) {
    refrescoEnVuelo = pedirRefresco().finally(() => {
      refrescoEnVuelo = null;
    });
  }
  return refrescoEnVuelo;
}

/**
 * `fetch` autenticado. Agrega el Bearer; ante un 401 refresca una vez y reintenta. Si no se puede,
 * borra los tokens, avisa a la app (que vuelve a /login guardando la ruta) y lanza "Sesión expirada".
 */
export async function fetchConSesion(url, init = {}) {
  const enviar = (token) => {
    const headers = { ...init.headers };
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetchRed(url, { ...init, headers });
  };
  const usado = leerAcceso();
  let respuesta = await enviar(usado);
  if (respuesta.status !== 401) return respuesta;

  // Otra petición ya renovó el token mientras esta viajaba: basta reintentar con el nuevo.
  const actual = leerAcceso();
  const nuevo = actual && actual !== usado ? actual : await refrescarSesion();
  if (nuevo) {
    respuesta = await enviar(nuevo);
    if (respuesta.status !== 401) return respuesta;
  }
  perderSesion();
  const error = new Error("Tu sesión expiró. Inicia sesión de nuevo.");
  error.status = 401;
  throw error;
}
