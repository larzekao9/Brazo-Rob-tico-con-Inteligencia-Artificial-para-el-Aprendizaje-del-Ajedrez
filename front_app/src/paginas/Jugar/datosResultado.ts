import {CATEGORIAS, caidaDeJugada, clasificarJugada} from '../../dominio/aprendizaje';
import type {CalidadJugada, JugadaHistorial} from '../../componentes/HistorialJugadas';

/** Una jugada de GET /partida/{id}/analisis-completo (campos que usa esta pantalla). */
export interface JugadaAnalizada {
  numero_ply: number;
  color: string;
  quien: string;
  jugada_san: string;
  evaluacion_cp: number | null;
  mate_en: number | null;
  mejor_jugada_motor: string | null;
  evaluacion_mejor_cp: number | null;
  mate_en_mejor: number | null;
  calidad: string;
  explicacion: string;
}

export interface Calibracion {
  registrada: boolean;
  motivo?: string | null;
  es_diagnostico?: boolean;
  precision_partida?: number | null;
  precision_promedio?: number | null;
  nivel?: number | null;
  nivel_anterior?: number | null;
  rango?: string | null;
  rango_anterior?: string | null;
  cambio_de_nivel?: number;
  cambio_de_rango?: boolean;
}

export interface AnalisisCompleto {
  partida_id: string;
  jugadas: JugadaAnalizada[];
  resumen: {precision_jugador: number | null; consejo_tutor: string; total_jugadas: number} | null;
  calibracion?: Calibracion | null;
}

/** Tope vertical (cp) al que se recortan los mates en la curva. */
export const TOPE_MATE_CP = 800;

/** Evaluación de una jugada desde las blancas: el backend la manda desde quien movió. */
export function evaluacionBlancas(jugada: JugadaAnalizada): number {
  const signo = jugada.color === 'blanco' ? 1 : -1;
  // mate_en = 0: la jugada dio mate (el rival ya no tiene movimientos); a favor de quien jugó.
  if (jugada.mate_en !== null) return (jugada.mate_en === 0 ? 1 : Math.sign(jugada.mate_en)) * signo * TOPE_MATE_CP;
  return (jugada.evaluacion_cp ?? 0) * signo;
}

/** Serie para GraficoEvaluacion, con el inicio en 0 para que la curva parta del equilibrio. */
export function curvaDeEvaluacion(jugadas: JugadaAnalizada[]): number[] {
  return jugadas.length === 0 ? [] : [0, ...jugadas.map(evaluacionBlancas)];
}

/** Texto de la evaluación final ("+1.2", "-2.1", "Mate") o "—" si no hay datos. */
export function textoEvaluacionFinal(jugadas: JugadaAnalizada[]): string {
  const ultima = jugadas[jugadas.length - 1];
  if (!ultima) return '—';
  if (ultima.mate_en !== null) return 'Mate';
  if (ultima.evaluacion_cp === null) return '—';
  const pawns = evaluacionBlancas(ultima) / 100;
  return `${pawns > 0 ? '+' : ''}${pawns.toFixed(1)}`;
}

const CALIDAD_A_INSIGNIA: Partial<Record<string, CalidadJugada>> = {
  brillante: 'brillante',
  mejor: 'mejor',
  error: 'error',
  blunder: 'blunder',
  colgada_grave: 'blunder',
};

/** Jugadas en el formato de HistorialJugadas, con la insignia de calidad que calculó el backend. */
export function jugadasParaHistorial(jugadas: JugadaAnalizada[]): JugadaHistorial[] {
  return jugadas.map((j) => ({san: j.jugada_san, calidad: CALIDAD_A_INSIGNIA[j.calidad]}));
}

export interface ErrorDelJugador {
  jugada: JugadaAnalizada;
  categoria: string;
}

/** Hasta `maximo` jugadas del jugador que perdieron más ventaja (inexactitud, error o blunder). */
export function peoresErrores(jugadas: JugadaAnalizada[], maximo = 5): ErrorDelJugador[] {
  const graves: string[] = [CATEGORIAS.INEXACTITUD, CATEGORIAS.ERROR, CATEGORIAS.BLUNDER];
  return jugadas
    .filter((j) => j.quien === 'jugador')
    .map((jugada) => ({jugada, categoria: clasificarJugada(jugada) as string}))
    .filter((e) => graves.includes(e.categoria))
    .sort((a, b) => caidaDeJugada(b.jugada) - caidaDeJugada(a.jugada))
    .slice(0, maximo)
    .sort((a, b) => a.jugada.numero_ply - b.jugada.numero_ply);
}
