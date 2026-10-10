// Copia de frontend/src/aprendizaje.js (ver PLAN_FRONT_APP.md §2.3). Mantener alineado con el original.
/**
 * Utilidades puras para la vista de Aprendizaje: clasificación de jugadas a
 * partir del análisis completo que devuelve el backend. Sin JSX, sin fetch —
 * solo cálculo, para poder probarlas sin backend ni DOM (mismo criterio que
 * ajedrez.js).
 */

/**
 * Probabilidad estimada de ganar (0-100) a partir de una evaluación en
 * centipawns o de un mate forzado, desde la perspectiva de quien tiene el
 * turno en esa jugada. Fórmula pública de Lichess (win rate model) — no
 * cambiarla sin motivo, ya está validada.
 */
export function winPercent(evaluacionCp, mateEn) {
  if (mateEn !== null && mateEn !== undefined) {
    return mateEn > 0 ? 100 : 0;
  }
  return 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * evaluacionCp)) - 1);
}

import { PIEZAS } from './contenido/piezas';

export const CATEGORIAS = {
  MEJOR: "mejor",
  BUENA: "buena",
  INEXACTITUD: "inexactitud",
  ERROR: "error",
  BLUNDER: "blunder",
};

/** Calidad del backend (7 niveles) a las 5 categorías de esta vista. */
const CALIDAD_BACKEND_A_CATEGORIA = {
  brillante: CATEGORIAS.MEJOR,
  mejor: CATEGORIAS.MEJOR,
  excelente: CATEGORIAS.BUENA,
  buena: CATEGORIAS.BUENA,
  imprecision: CATEGORIAS.INEXACTITUD,
  error: CATEGORIAS.ERROR,
  blunder: CATEGORIAS.BLUNDER,
  colgada_grave: CATEGORIAS.BLUNDER,
};

/**
 * Clasifica una jugada del análisis completo según cuánto bajó el
 * winPercent respecto a la mejor jugada posible en esa posición, siempre en
 * la perspectiva de quien la jugó (evaluacion_cp/evaluacion_mejor_cp ya
 * vienen en esa perspectiva, no hace falta invertir signos acá).
 */
export function clasificarJugada(jugada) {
  // La calidad que calcula el backend ya contempla mates (un mate recibido es blunder)
  // y no depende de la caída de winPercent, que no representa bien los mates.
  const porBackend = CALIDAD_BACKEND_A_CATEGORIA[jugada.calidad];
  if (porBackend) return porBackend;
  if (jugada.jugada_san === jugada.mejor_jugada_motor) {
    return CATEGORIAS.MEJOR;
  }
  const caida = caidaDeJugada(jugada);
  if (caida >= 30) return CATEGORIAS.BLUNDER;
  if (caida >= 20) return CATEGORIAS.ERROR;
  if (caida >= 10) return CATEGORIAS.INEXACTITUD;
  return CATEGORIAS.BUENA;
}

/** Caída de winPercent entre la mejor jugada posible y la jugada real (siempre >= 0). */
export function caidaDeJugada(jugada) {
  const winPercentMejor = winPercent(jugada.evaluacion_mejor_cp, jugada.mate_en_mejor);
  const winPercentReal = winPercent(jugada.evaluacion_cp, jugada.mate_en);
  return Math.max(0, winPercentMejor - winPercentReal);
}

/** Color/ícono/etiqueta de cada categoría — mismos tokens Tailwind del resto del proyecto (ver index.css). */
export const ESTILO_CATEGORIA = {
  [CATEGORIAS.MEJOR]: {
    etiqueta: "Mejor jugada",
    texto: "text-primary",
    fondo: "bg-primary-container/20",
    icono: "stars",
  },
  [CATEGORIAS.BUENA]: {
    etiqueta: "Buena",
    texto: "text-primary",
    fondo: "bg-surface-container",
    icono: "check_circle",
  },
  [CATEGORIAS.INEXACTITUD]: {
    etiqueta: "Inexactitud",
    texto: "text-secondary",
    fondo: "bg-secondary-container/20",
    icono: "help",
  },
  [CATEGORIAS.ERROR]: {
    etiqueta: "Error",
    texto: "text-tertiary-fixed-dim",
    fondo: "bg-tertiary-container/20",
    icono: "warning",
  },
  [CATEGORIAS.BLUNDER]: {
    etiqueta: "Blunder",
    texto: "text-error",
    fondo: "bg-error-container/30",
    icono: "report",
  },
};

/** Texto corto de "cómo mejorar" por categoría — plantillas fijas, no generación libre. */
export function comoMejorarPorCategoria(categoria) {
  switch (categoria) {
    case CATEGORIAS.MEJOR:
      return "Esta fue la jugada más fuerte según el análisis del motor — nada que corregir acá.";
    case CATEGORIAS.BUENA:
      return "Jugada sólida, sin pérdida relevante de ventaja. Seguí buscando la idea más precisa cuando el reloj lo permita.";
    case CATEGORIAS.INEXACTITUD:
      return "Había una jugada algo mejor disponible, pero la diferencia es chica — no es grave.";
    case CATEGORIAS.ERROR:
      return "Esta jugada cede una ventaja apreciable. Revisá si dejaste una pieza peor colocada o ignoraste una amenaza del rival.";
    case CATEGORIAS.BLUNDER:
      return "Revisá si dejaste una pieza sin defender, permitiste una combinación táctica o abriste un jaque — acá se perdió la mayor parte de la ventaja.";
    default:
      return "";
  }
}

/**
 * `true` si la jugada la hizo el estudiante. Usa `quien` del backend; si no viene,
 * deduce por paridad (el estudiante juega primero: plies impares).
 */
export function esDelJugador(jugada) {
  if (!jugada) return false;
  return jugada.quien ? jugada.quien === "jugador" : jugada.numero_ply % 2 === 1;
}

/** Tipo de pieza que hizo una jugada en SAN: "Nf3" es caballo, "e4" es peón. */
export function tipoDePiezaSan(san) {
  return { K: "rey", Q: "dama", R: "torre", B: "alfil", N: "caballo" }[san?.[0]] ?? "peon";
}

const CONSEJO_PIEZA_AL_ERRAR = {
  rey: "Antes de mover al rey, mirá si la casilla de destino queda atacada: el rey no puede quedar en jaque.",
  dama: "La dama es la pieza más valiosa: no la pongas donde una pieza menor rival la pueda atacar con tempo.",
  torre: "La torre rinde más en filas o columnas abiertas. Antes de moverla, revisá que no deje otra pieza sin defensa.",
  alfil: "El alfil ataca en diagonal: buscá diagonales libres y no lo cambies por una pieza menor sin un motivo claro.",
  caballo: "El caballo salta, pero en el borde pierde fuerza. Antes de moverlo, mirá a qué casillas llega y qué amenazas genera.",
  peon: "Los peones no retroceden: antes de avanzarlo, mirá si deja casillas débiles cerca de tu rey o frente a una pieza rival.",
};

/**
 * Consejo para jugar mejor con la pieza que hizo la jugada. Para el estudiante
 * dice cómo usar su pieza y qué podía jugar; para la contraparte, qué aprender de cómo la usa.
 * `categoria` es la de `clasificarJugada`.
 */
export function comoMejorarJugada(jugada, categoria) {
  if (!jugada) return "";
  const tipo = tipoDePiezaSan(jugada.jugada_san);
  const pieza = PIEZAS.find((p) => p.tipo === tipo) ?? null;
  const nombre = pieza ? pieza.nombre.toLowerCase() : "pieza";
  const articulo = pieza?.articulo ?? "la";

  if (!esDelJugador(jugada)) {
    const como = pieza ? ` Así se mueve ${articulo} ${nombre}: ${pieza.comoSeMueve}` : "";
    return `Mirá cómo usa la contraparte ${articulo} ${nombre} en esta posición.${como}`;
  }

  if (categoria === CATEGORIAS.MEJOR || categoria === CATEGORIAS.BUENA) {
    return pieza ? `Buen uso de tu ${nombre}. Recordá cómo se mueve: ${pieza.comoSeMueve}` : comoMejorarPorCategoria(categoria);
  }

  const consejo = CONSEJO_PIEZA_AL_ERRAR[tipo] ?? comoMejorarPorCategoria(categoria);
  const mejor = jugada.mejor_jugada_motor;
  if (!mejor || mejor === jugada.jugada_san) return consejo;

  const piezaMejor = PIEZAS.find((p) => p.tipo === tipoDePiezaSan(mejor)) ?? null;
  const cuerpoMejor = piezaMejor
    ? ` Lo que podías jugar era ${mejor}: con ${piezaMejor.articulo} ${piezaMejor.nombre.toLowerCase()}, ${piezaMejor.comoSeMueve.charAt(0).toLowerCase()}${piezaMejor.comoSeMueve.slice(1)}`
    : ` Lo que podías jugar era ${mejor}.`;
  return `${consejo}${cuerpoMejor}`;
}
