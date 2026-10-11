// Endpoints que backend.js (copia de frontend/src/api/backend.js) no exporta.
// Mismo manejo de token y errores que ese archivo: token JWT en localStorage ("access_token").

async function solicitarGet(endpoint) {
  let token = null;
  try {
    token = localStorage.getItem("access_token");
  } catch {
    token = null;
  }
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const respuesta = await fetch(endpoint, { method: "GET", headers });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  return respuesta.json();
}

/**
 * Estadísticas del jugador autenticado (HU14): total_partidas, partidas_ganadas,
 * partidas_perdidas, partidas_tablas, win_percent_promedio, racha_victoria_actual,
 * precision_promedio y top_errores [{tipo, cantidad}].
 */
export function obtenerEstadisticasUsuario() {
  return solicitarGet("/usuario/estadisticas");
}

/**
 * Termina una partida en curso como abandono del jugador (derrota de las blancas).
 * Usa `POST /partida/{id}/tiempo-agotado`, que el backend documenta como equivalente a
 * abandonar; la partida queda terminada y cuenta para historial y estadísticas.
 * 400 si la partida no tiene jugadas todavía.
 */
export async function abandonarPartida(partidaId) {
  let token = null;
  try {
    token = localStorage.getItem("access_token");
  } catch {
    token = null;
  }
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const respuesta = await fetch(`/partida/${encodeURIComponent(partidaId)}/tiempo-agotado`, {
    method: "POST",
    headers,
    body: JSON.stringify({ lado: "blancas" }),
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const error = new Error(typeof detalle?.detail === "string" ? detalle.detail : `Error ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  return respuesta.json();
}
