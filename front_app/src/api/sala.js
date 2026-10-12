// Capa de comunicación con el backend para salas (humano vs humano). Contratos: backend/esquemas/sala.py.
// Solo fetch; el token, el refresh ante 401 y los errores legibles viven en sesionHttp.js.

import { errorDeRespuesta, fetchConSesion } from "./sesionHttp.js";

async function pedir(endpoint, metodo = "GET", cuerpo) {
  const init = { method: metodo, headers: { "Content-Type": "application/json" } };
  if (cuerpo !== undefined) init.body = JSON.stringify(cuerpo);
  const respuesta = await fetchConSesion(endpoint, init);
  if (!respuesta.ok) throw await errorDeRespuesta(respuesta);
  if (respuesta.status === 204) return null;
  return respuesta.json();
}

const rutaSala = (codigo) => `/sala/${encodeURIComponent(codigo)}`;

/** Crea una sala. `color`: "blancas" | "negras" | "aleatorio". */
export function crearSala(color) {
  return pedir("/sala", "POST", { color });
}

/** Se une a la sala (idempotente). Devuelve `{codigo, partida_id, rol}`; "espectador" si está llena. */
export function unirseASala(codigo) {
  return pedir(`${rutaSala(codigo)}/unirse`, "POST");
}

/** Estado actual de la sala (el que se consulta por polling). */
export function obtenerSala(codigo) {
  return pedir(rutaSala(codigo), "GET");
}

/** Juega una jugada UCI (ej. "e2e4"). Devuelve la sala ya actualizada. */
export function moverEnSala(codigo, jugada) {
  return pedir(`${rutaSala(codigo)}/mover`, "POST", { jugada });
}

/** Abandona la partida: gana el rival. Devuelve la sala. */
export function abandonarSala(codigo) {
  return pedir(`${rutaSala(codigo)}/abandonar`, "POST");
}

/** Cancela una sala que sigue esperando rival (solo su creador). */
export function cancelarSala(codigo) {
  return pedir(rutaSala(codigo), "DELETE");
}

/** Análisis general con Stockfish (solo si la partida terminó; antes responde 400). */
export function analisisSala(codigo) {
  return pedir(`${rutaSala(codigo)}/analisis`, "GET");
}

/** Sala `esperando` o `en_curso` más reciente del usuario, o `null`. */
export function salaActiva() {
  return pedir("/sala/activa", "GET");
}

/** Casillas destino legales de la pieza en `casilla` (el backend responde `{casillas: [...]}`). */
export async function jugadasLegalesSala(codigo, casilla) {
  const datos = await pedir(`${rutaSala(codigo)}/jugadas-legales?casilla=${encodeURIComponent(casilla)}`, "GET");
  return datos?.casillas ?? [];
}
