async function solicitar(endpoint, opciones) {
  const respuesta = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
  }
  return respuesta.json();
}

export function calcularJugada(fen, nivel) {
  return solicitar("/jugada", { body: JSON.stringify({ fen, nivel }) });
}

export function analizarPosicion(fen, nivel) {
  return solicitar("/analisis", { body: JSON.stringify({ fen, nivel }) });
}

export function crearPartida(nivel) {
  return solicitar("/partida", { body: JSON.stringify({ nivel }) });
}

export function moverPartida(partidaId, jugada) {
  return solicitar(`/partida/${partidaId}/mover`, { body: JSON.stringify({ jugada }) });
}
