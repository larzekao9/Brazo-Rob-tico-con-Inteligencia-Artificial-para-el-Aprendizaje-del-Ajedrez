/** Definición corta por principio ajedrecístico: lenguaje simple, un término tocable por jugada. */
export interface Termino {
  termino: string;
  definicion: string;
}

export const TERMINOS: Record<string, Termino> = {
  pieza_indefensa: {termino: 'pieza colgada', definicion: 'Una pieza que el rival puede capturar gratis porque nadie la defiende.'},
  control_del_centro: {termino: 'control del centro', definicion: 'Dominar las casillas centrales (d4, d5, e4, e5). Desde ahí tus piezas llegan a más lugares.'},
  desarrollo_piezas: {termino: 'desarrollo de piezas', definicion: 'Sacar los caballos y alfiles de su casilla inicial para que puedan entrar al juego.'},
  seguridad_del_rey: {termino: 'enroque', definicion: 'Una jugada especial que pone al rey a resguardo y activa una torre, en un solo movimiento.'},
  oportunidad_tactica: {termino: 'táctica', definicion: 'Una jugada o serie de jugadas que ganan material o dan jaque mate por sorpresa.'},
  iniciativa_tactica: {termino: 'iniciativa', definicion: 'Cuando tus jugadas obligan al rival a defenderse, en vez de dejarlo seguir su propio plan.'},
  jaque_mate: {termino: 'jaque mate', definicion: 'Un jaque del que el rey no tiene forma de escapar. Termina la partida.'},
  imprecision_posicional: {termino: 'imprecisión', definicion: 'Una jugada que no es grave, pero deja pasar una opción algo mejor.'},
  error_tactico: {termino: 'error táctico', definicion: 'Una jugada que le regala ventaja al rival por no ver una amenaza.'},
  colgada_grave: {termino: 'blunder', definicion: 'Un error grande, de los que pierden una pieza importante o la partida.'},
  posicion_solida: {termino: 'posición sólida', definicion: 'Tus piezas están bien colocadas y no hay debilidades claras para atacar.'},
  maestria_tactica: {termino: 'jugada brillante', definicion: 'Una jugada excepcional, a veces un sacrificio, que rompe la posición del rival.'},
  general: {termino: 'jugada', definicion: 'El movimiento que elegiste en esa posición del tablero.'},
};

const TERMINOS_GENERALES: Termino[] = [
  {termino: 'centipawns', definicion: 'La unidad que usa el motor para medir la ventaja. 100 centipawns equivalen, más o menos, a un peón de diferencia.'},
  {termino: 'motor de ajedrez', definicion: 'Un programa (como Stockfish) que calcula millones de jugadas para decir cuál es la mejor en una posición.'},
];

/** Términos de una jugada: el propio del principio más los generales. */
export function terminosDeJugada(principio: string | undefined): Termino[] {
  return [TERMINOS[principio ?? ''] ?? TERMINOS.general, ...TERMINOS_GENERALES];
}

/** Nombre legible de cada clave interna de `principio_ajedrecistico`. */
export const NOMBRE_PRINCIPIO: Record<string, string> = {
  jaque_mate: 'Jaque mate',
  seguridad_del_rey: 'Seguridad del rey',
  pieza_indefensa: 'Pieza indefensa',
  oportunidad_tactica: 'Oportunidad táctica',
  control_del_centro: 'Control del centro',
  desarrollo_piezas: 'Desarrollo de piezas',
  iniciativa_tactica: 'Iniciativa táctica',
  maestria_tactica: 'Maestría táctica',
  posicion_solida: 'Posición sólida',
  imprecision_posicional: 'Imprecisión posicional',
  error_tactico: 'Error táctico',
  colgada_grave: 'Blunder (colgada grave)',
  general: 'Jugada general',
};

/**
 * Qué tan grave o buena fue una jugada, según la `calidad` que ya calculó el backend. Se rankea por
 * severidad real y, en empate, se prefiere la más reciente (la que el jugador recuerda mejor).
 */
const RANGO_PEOR: Record<string, number> = {blunder: 3, error: 2, imprecision: 1};
const RANGO_MEJOR: Record<string, number> = {brillante: 3, mejor: 2, excelente: 1};

function masNotable<T extends {calidad: string}>(jugadas: T[], rangoPorCalidad: Record<string, number>): T | null {
  let elegida: T | null = null;
  let mejorRango = 0;
  for (const jugada of jugadas) {
    const rango = rangoPorCalidad[jugada.calidad] ?? 0;
    if (rango > 0 && rango >= mejorRango) {
      mejorRango = rango;
      elegida = jugada;
    }
  }
  return elegida;
}

/** Hasta 2 jugadas para repasar: la peor y la mejor. Si fue pareja, cae a la última jugada; nunca inventa una segunda. */
export function jugadasParaRepasar<T extends {calidad: string}>(jugadasDelJugador: T[]): T[] {
  if (jugadasDelJugador.length === 0) return [];
  const peor = masNotable(jugadasDelJugador, RANGO_PEOR);
  const mejor = masNotable(jugadasDelJugador, RANGO_MEJOR);
  if (peor && mejor) return [peor, mejor];
  if (peor || mejor) return [(peor ?? mejor) as T];
  return [jugadasDelJugador[jugadasDelJugador.length - 1]];
}
