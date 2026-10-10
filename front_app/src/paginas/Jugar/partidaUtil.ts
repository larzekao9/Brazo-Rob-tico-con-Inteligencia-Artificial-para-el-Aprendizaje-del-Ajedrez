import {turnoDeFen} from '../../dominio/ajedrez';
import type {Color} from '../../dominio/tablero';

/** Estado de una partida tal como lo devuelve GET /partida/{id}. */
export interface EstadoPartida {
  id: string;
  tipo_oponente: string;
  nivel: number;
  fen: string;
  fen_inicial: string;
  terminada: boolean;
  resultado: string | null;
  jugadas: string[];
}

/** Variante candidata de /mover (evaluación desde el punto de vista de quien mueve en `fen`). */
interface Variante {
  evaluacion_cp: number | null;
  mate_en: number | null;
}

/** Respuesta de POST /partida/{id}/mover. */
export interface RespuestaMover {
  fen: string;
  jugada_motor: string | null;
  terminada: boolean;
  resultado: string | null;
  jugadas: string[];
  variantes_candidatas: Variante[];
  retroalimentacion_en_vivo: {probabilidad_victoria: number} | null;
}

export interface Evaluacion {
  /** Centipeones desde las blancas (positivo = ventaja blanca). */
  cp: number | null;
  /** Jugadas hasta el mate; positivo = mate a favor de las blancas. */
  mate: number | null;
}

/**
 * El backend evalúa desde quien tiene el turno (Stockfish `pov(turno)`). La barra
 * y las curvas usan siempre las blancas: si mueven las negras se invierte el signo.
 */
export function evaluacionDesdeBlancas(fen: string, cp: number | null, mate: number | null): Evaluacion {
  const signo = turnoDeFen(fen) === 'b' ? -1 : 1;
  return {cp: cp === null ? null : cp * signo, mate: mate === null ? null : mate * signo};
}

/** Evaluación de la mejor variante de una respuesta de /mover, o null si no vino ninguna. */
export function evaluacionDeRespuesta(respuesta: RespuestaMover): Evaluacion | null {
  const mejor = respuesta.variantes_candidatas?.[0];
  if (!mejor || (mejor.evaluacion_cp === null && mejor.mate_en === null)) return null;
  return evaluacionDesdeBlancas(respuesta.fen, mejor.evaluacion_cp, mejor.mate_en);
}

/** Quién juega abajo: el humano mueve primero, así que es el color que mueve en la posición inicial. */
export function colorDelJugador(fenInicial: string): Color {
  return turnoDeFen(fenInicial) as Color;
}

export type Veredicto = 'victoria' | 'derrota' | 'tablas';

/** Traduce "1-0" / "0-1" / "1/2-1/2" a victoria, derrota o tablas para el jugador. */
export function veredictoDe(resultado: string | null, colorJugador: Color): Veredicto | null {
  if (resultado === '1/2-1/2') return 'tablas';
  if (resultado === '1-0') return colorJugador === 'w' ? 'victoria' : 'derrota';
  if (resultado === '0-1') return colorJugador === 'b' ? 'victoria' : 'derrota';
  return null;
}

/**
 * Resalta el destino de la jugada del rival. El backend devuelve la jugada en SAN y no
 * en UCI, así que solo se conoce la casilla destino: se manda "e5e5" para marcar esa casilla.
 */
export function ultimaJugadaDeSan(destino: string | null): string | null {
  return destino ? `${destino}${destino}` : null;
}
