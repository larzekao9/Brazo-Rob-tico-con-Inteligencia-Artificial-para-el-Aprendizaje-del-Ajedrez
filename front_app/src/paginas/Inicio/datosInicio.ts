import {precisionAPorcentaje} from '../../dominio/nivelJugador';
import type {EjeRadar} from '../../componentes/RadarHabilidades';
import type {Estadisticas, Usuario} from '../../estado/SesionContext';

/** Respuesta de GET /auth/nivel (solo lo que usa el Inicio). */
export interface NivelJugador {
  nivel_estimado: number | null;
  rango_estimado: string | null;
  partidas_calibradas: number;
  precision_promedio: number | null;
  progreso_siguiente_nivel: number | null;
  precision_siguiente_nivel: number | null;
}

/** Partidas jugadas que equivalen al 100 % del eje "Práctica" del radar. */
const PARTIDAS_PARA_PRACTICA_COMPLETA = 20;
const NIVEL_MAX = 20;

const FRASES = [
  'La disciplina de hoy es el progreso de mañana.',
  'Cada partida es una oportunidad para ser mejor.',
  'Las derrotas también forman parte del progreso.',
  'Piensa dos veces, mueve una.',
  'El mejor momento para mejorar es la próxima partida.',
];

/** Frase fija por día (no cambia entre renders del mismo día). */
export function fraseDelDia(fecha = new Date()): string {
  const diaDelAnio = Math.floor((fecha.getTime() - new Date(fecha.getFullYear(), 0, 0).getTime()) / 86_400_000);
  return FRASES[diaDelAnio % FRASES.length];
}

const acotar = (valor: number) => Math.max(0, Math.min(100, valor));

/**
 * Ejes del radar calculados solo con datos reales del backend. El backend no
 * desglosa habilidades por fase (aperturas, finales...), así que se usan cinco
 * métricas medidas. Un eje sin dato vale 0 y se rotula con "—".
 */
export function ejesDeRadar(estadisticas: Estadisticas | null, usuario: Usuario): EjeRadar[] {
  const total = estadisticas?.total_partidas ?? 0;
  const conPartidas = estadisticas !== null && total > 0;
  // El backend manda 0 cuando todavía no hay jugadas analizadas: se trata como "sin dato".
  const precision = conPartidas && estadisticas.precision_promedio > 0 ? precisionAPorcentaje(estadisticas.precision_promedio) : null;
  const ventaja = conPartidas ? estadisticas.win_percent_promedio : null;
  const victorias = conPartidas ? (estadisticas.partidas_ganadas / total) * 100 : null;
  const nivel = usuario.nivel_estimado != null ? (usuario.nivel_estimado / NIVEL_MAX) * 100 : null;
  const practica = estadisticas !== null ? (total / PARTIDAS_PARA_PRACTICA_COMPLETA) * 100 : null;
  const dato = (nombre: string, valor: number | null): EjeRadar => ({nombre, valor: valor === null ? 0 : acotar(valor)});
  return [dato('Precisión', precision), dato('Ventaja', ventaja), dato('Victorias', victorias), dato('Nivel', nivel), dato('Práctica', practica)];
}

export const textoPorcentaje = (valor: number | null | undefined): string =>
  typeof valor === 'number' && !Number.isNaN(valor) ? `${Math.round(valor)}%` : '—';
