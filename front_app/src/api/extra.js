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
