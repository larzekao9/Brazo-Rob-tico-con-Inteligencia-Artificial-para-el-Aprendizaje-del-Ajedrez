import type {CalidadJugada, JugadaHistorial} from '../../componentes/HistorialJugadas';
import type {Color} from '../../dominio/tablero';
import {TOPE_MATE_CP} from '../Jugar/datosResultado';
import type {ErrorApi, JugadaAnalisis, PuntoCurva, RolSala, SalaEstado} from './tipos';

/** Texto de error de la capa api/ (ya viene legible); `porDefecto` si no es un Error. */
export function mensajeDeError(err: unknown, porDefecto: string): string {
  return err instanceof Error && err.message ? err.message : porDefecto;
}

/** true si el fallo fue de conexión (red caída o 5xx): ahí tiene sentido ofrecer Reintentar. */
export function esErrorDeConexion(err: unknown): boolean {
  return err instanceof Error && (err as ErrorApi).sinConexion === true;
}

/** Color que se ve abajo: el del jugador; el espectador mira desde las blancas. */
export function colorDeRol(rol: RolSala): Color {
  return rol === 'negras' ? 'b' : 'w';
}

export function turnoComoColor(turno: SalaEstado['turno']): Color {
  return turno === 'negras' ? 'b' : 'w';
}

export interface TextoFin {
  titulo: string;
  detalle: string;
  tono: 'victoria' | 'derrota' | 'neutro';
}

const DETALLE_TABLAS = 'Tablas: ningún bando puede ganar.';

/** Qué decir al terminar la partida, según quién mira (Ganaste / Perdiste / Tablas / Ganaron las blancas). */
export function textoDeFin(sala: SalaEstado): TextoFin {
  const {resultado, motivo_fin: motivo, rol} = sala;
  if (motivo === 'inactividad' || resultado === null) {
    return {titulo: 'Partida cancelada por inactividad', detalle: 'Nadie ganó: la sala venció por falta de actividad.', tono: 'neutro'};
  }
  if (resultado === '1/2-1/2') return {titulo: 'Tablas', detalle: DETALLE_TABLAS, tono: 'neutro'};
  const ganador: 'blancas' | 'negras' = resultado === '1-0' ? 'blancas' : 'negras';
  const razon = motivo === 'abandono' ? 'por abandono' : 'por jaque mate';
  if (rol === 'espectador') {
    return {titulo: `Ganaron las ${ganador}`, detalle: `Victoria de las ${ganador} ${razon}.`, tono: 'neutro'};
  }
  if (rol === ganador) {
    return {titulo: 'Ganaste', detalle: motivo === 'abandono' ? 'Tu rival abandonó la partida.' : 'Ganaste por jaque mate.', tono: 'victoria'};
  }
  return {titulo: 'Perdiste', detalle: motivo === 'abandono' ? 'Abandonaste la partida.' : 'Perdiste por jaque mate.', tono: 'derrota'};
}

/**
 * Curva del backend (desde las blancas) a `number[]` para GraficoEvaluacion, con el inicio en 0.
 * Mismo criterio de mate que Jugar/datosResultado: los mates se acotan a +-TOPE_MATE_CP;
 * `mate_en === 0` significa que esa jugada dio mate, a favor de quien la jugó (ply impar = blancas).
 */
export function curvaParaGrafico(curva: PuntoCurva[]): number[] {
  if (curva.length === 0) return [];
  const valores = curva.map((punto) => {
    if (punto.mate_en !== null) {
      const signo = punto.mate_en === 0 ? (punto.ply % 2 === 1 ? 1 : -1) : Math.sign(punto.mate_en);
      return signo * TOPE_MATE_CP;
    }
    return punto.evaluacion_cp ?? 0;
  });
  return [0, ...valores];
}

const INSIGNIA_DE_CALIDAD: Partial<Record<string, CalidadJugada>> = {
  brillante: 'brillante',
  mejor: 'mejor',
  error: 'error',
  blunder: 'blunder',
  colgada_grave: 'blunder',
};

/** Jugadas del análisis en el formato de HistorialJugadas (insignia de calidad incluida). */
export function jugadasParaHistorial(jugadas: JugadaAnalisis[]): JugadaHistorial[] {
  return jugadas.map((j) => ({san: j.jugada_san, calidad: INSIGNIA_DE_CALIDAD[j.calidad]}));
}

const NOMBRE_DE_CALIDAD: Record<string, string> = {
  brillante: 'Brillante',
  mejor: 'Mejor jugada',
  bueno: 'Buena',
  buena: 'Buena',
  excelente: 'Excelente',
  imprecision: 'Imprecisión',
  error: 'Error',
  blunder: 'Error grave',
  colgada_grave: 'Pieza colgada',
};

/** Etiqueta legible de la calidad de una jugada. */
export function nombreDeCalidad(calidad: string): string {
  return NOMBRE_DE_CALIDAD[calidad] ?? calidad;
}

/** Texto "74 %" para una precisión (0-100) o "—" si el bando no jugó. */
export function textoPrecision(precision: number | null): string {
  return precision === null ? '—' : `${Math.round(precision)} %`;
}
