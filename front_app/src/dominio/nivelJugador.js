// Copia de frontend/src/nivelJugador.js (ver PLAN_FRONT_APP.md §2.3). Mantener alineado con el original.
/**
 * Escala de niveles del jugador y utilidades puras para mostrarla. Sin JSX ni
 * fetch — solo constantes y cálculo, para poder razonar sobre ellas sin DOM
 * (mismo criterio que ajedrez.js y aprendizaje.js).
 *
 * El nivel del jugador (0-20) lo calcula el backend comparando las jugadas del
 * jugador con las de Stockfish; el modelo Turing no interviene en ese cálculo.
 */

/** Techo de Stockfish (Skill Level 0-20). */
export const NIVEL_MAX_STOCKFISH = 20;

/**
 * Techo de Turing: fue entrenado con partidas de maestros, por eso su nivel más
 * alto es "Maestro" (18). Los niveles 19 y 20 solo existen en Stockfish.
 */
export const NIVEL_MAX_MODELO = 18;

/** Nivel fijo de Stockfish contra el que se juega la primera partida (diagnóstico). */
export const NIVEL_DIAGNOSTICO = 8;

/** Bandas por defecto, por si el backend todavía no manda `escala.bandas`. */
export const BANDAS_POR_DEFECTO = {
  Principiante: [0, 6],
  Intermedio: [7, 13],
  Avanzado: [14, 20],
};

/** Rango (Principiante/Intermedio/Avanzado) al que pertenece un nivel, según las bandas dadas. */
export function rangoDeNivel(nivel, bandas = BANDAS_POR_DEFECTO) {
  if (typeof nivel !== 'number') return null;
  for (const [rango, [desde, hasta]] of Object.entries(bandas)) {
    if (nivel >= desde && nivel <= hasta) return rango;
  }
  return null;
}

/**
 * Convierte una precisión del backend a porcentaje redondeado (0-100). El
 * backend la manda como porcentaje; por si alguna vez llega como fracción
 * (0-1) también se entiende — una precisión real de 1 % o menos no existe en
 * una partida jugada, así que no hay ambigüedad práctica.
 */
export function precisionAPorcentaje(valor) {
  if (typeof valor !== 'number' || Number.isNaN(valor)) return null;
  const porcentaje = valor <= 1 ? valor * 100 : valor;
  return Math.round(Math.min(100, Math.max(0, porcentaje)));
}

function pluralNiveles(cantidad) {
  return `${cantidad} ${cantidad === 1 ? 'nivel' : 'niveles'}`;
}

/**
 * Texto del cambio de nivel tras calibrar una partida, o `null` si no hubo
 * cambio (o si es el diagnóstico inicial, donde no hay nivel medido previo con
 * el que comparar). Devuelve `{ sube, principal, detalle }`.
 */
export function describirCambioNivel(calibracion) {
  if (!calibracion || calibracion.es_diagnostico) return null;

  let delta = calibracion.cambio_de_nivel;
  if (typeof delta !== 'number') {
    delta =
      typeof calibracion.nivel === 'number' && typeof calibracion.nivel_anterior === 'number'
        ? calibracion.nivel - calibracion.nivel_anterior
        : 0;
  }
  if (delta === 0) return null;

  const sube = delta > 0;
  const absoluto = Math.abs(delta);
  const detalle = `${sube ? '+' : '-'}${pluralNiveles(absoluto)}`;

  if (calibracion.cambio_de_rango && calibracion.rango_anterior && calibracion.rango) {
    return {
      sube,
      principal: `${sube ? 'Subiste' : 'Bajaste'} de ${calibracion.rango_anterior} a ${calibracion.rango}`,
      detalle,
    };
  }
  return {
    sube,
    principal: `${sube ? 'Subiste' : 'Bajaste'} ${pluralNiveles(absoluto)}`,
    detalle,
  };
}
