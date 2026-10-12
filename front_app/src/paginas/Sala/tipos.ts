/** Contratos de la API de salas (backend/esquemas/sala.py). */

export type RolSala = 'blancas' | 'negras' | 'espectador';
export type EstadoSala = 'esperando' | 'en_curso' | 'terminada' | 'abandonada';
export type MotivoFin = 'mate' | 'tablas' | 'abandono' | 'inactividad';

export interface JugadorSala {
  id: number;
  nombre: string;
  avatar_url: string | null;
}

/** GET /sala/{codigo}: estado de la sala desde el punto de vista de quien consulta (`rol`). */
export interface SalaEstado {
  codigo: string;
  partida_id: string;
  estado: EstadoSala;
  fen: string;
  turno: 'blancas' | 'negras';
  jugadas: string[];
  ultima_jugada_uci: string | null;
  terminada: boolean;
  /** "1-0" | "0-1" | "1/2-1/2"; null si no terminó o venció por inactividad. */
  resultado: string | null;
  motivo_fin: MotivoFin | null;
  blancas: JugadorSala | null;
  negras: JugadorSala | null;
  rol: RolSala;
  version: number;
}

/** GET /sala/activa devuelve el mismo contrato (o null). */
export type SalaActiva = SalaEstado;

export interface PuntoCurva {
  ply: number;
  evaluacion_cp: number | null;
  mate_en: number | null;
}

export interface ResumenBando {
  nombre: string | null;
  precision: number | null;
  mejores: number;
  imprecisiones: number;
  errores: number;
  blunders: number;
}

export interface JugadaAnalisis {
  numero_ply: number;
  color: 'blanco' | 'negro';
  jugada_san: string;
  fen_antes: string;
  calidad: string;
  perdida_cp: number;
  explicacion: string;
}

export interface MomentoClave {
  ply: number;
  color: 'blanco' | 'negro';
  jugada_san: string;
  calidad: string;
  perdida_cp: number;
  mejor_jugada_san: string | null;
  explicacion: string;
}

/** GET /sala/{codigo}/analisis. */
export interface AnalisisSala {
  codigo: string;
  resultado: string | null;
  motivo_fin: MotivoFin | null;
  total_jugadas: number;
  blancas: ResumenBando;
  negras: ResumenBando;
  curva: PuntoCurva[];
  momentos_clave: MomentoClave[];
  jugadas: JugadaAnalisis[];
}

/** Error de la capa api/: `status` HTTP y `sinConexion` (red caída o 5xx). */
export interface ErrorApi extends Error {
  status?: number;
  sinConexion?: boolean;
}
