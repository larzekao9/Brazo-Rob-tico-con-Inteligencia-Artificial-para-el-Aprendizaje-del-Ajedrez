// Endpoints que backend.js (copia de frontend/src/api/backend.js) no exporta.
// Token, refresh ante 401 y errores legibles: ver sesionHttp.js.
import { errorDeRespuesta, fetchConSesion } from "./sesionHttp.js";

async function pedir(endpoint, opciones) {
  const respuesta = await fetchConSesion(endpoint, {
    ...opciones,
    headers: { "Content-Type": "application/json" },
  });
  if (!respuesta.ok) throw await errorDeRespuesta(respuesta);
  return respuesta.json();
}

/**
 * Estadísticas del jugador autenticado (HU14): total_partidas, partidas_ganadas,
 * partidas_perdidas, partidas_tablas, win_percent_promedio, racha_victoria_actual,
 * precision_promedio y top_errores [{tipo, cantidad}].
 */
export function obtenerEstadisticasUsuario() {
  return pedir("/usuario/estadisticas", { method: "GET" });
}

/**
 * Termina una partida en curso como abandono del jugador (derrota de las blancas).
 * Usa `POST /partida/{id}/tiempo-agotado`, que el backend documenta como equivalente a
 * abandonar; la partida queda terminada y cuenta para historial y estadísticas.
 * 400 si la partida no tiene jugadas todavía.
 */
export function abandonarPartida(partidaId) {
  return pedir(`/partida/${encodeURIComponent(partidaId)}/tiempo-agotado`, {
    method: "POST",
    body: JSON.stringify({ lado: "blancas" }),
  });
}
