import {NIVEL_DIAGNOSTICO, NIVEL_MAX_MODELO, NIVEL_MAX_STOCKFISH, rangoDeNivel} from '../../dominio/nivelJugador';

/** Quién decide las jugadas del rival. El front solo manda este valor; el backend decide con quién juega. */
export type TipoOponente = 'motor' | 'modelo';

export const OPONENTES: Record<TipoOponente, {titulo: string; descripcion: string; insignia: string}> = {
  modelo: {
    titulo: 'Modelo IA (Neural)',
    descripcion: 'Nuestra red neuronal entrenada con partidas reales. Juega por su cuenta, con estilo humano.',
    insignia: 'IA propia',
  },
  motor: {
    titulo: 'Motor Stockfish',
    descripcion: 'El motor clásico de ajedrez, con niveles de dificultad de 0 a 20.',
    insignia: 'Motor clásico',
  },
};

export function esTipoOponente(valor: string | null): valor is TipoOponente {
  return valor === 'motor' || valor === 'modelo';
}

/** Va a la configuración dejando el oponente elegido en la URL (sobrevive a recargar la página). */
export function irAConfiguracion(oponente: TipoOponente): void {
  window.location.hash = `/jugar/config?oponente=${oponente}`;
}

/** Oponente elegido en la pantalla anterior; 'modelo' si la URL no lo trae. */
export function oponenteDeLaUrl(): TipoOponente {
  const consulta = window.location.hash.split('?')[1] ?? '';
  const valor = new URLSearchParams(consulta).get('oponente');
  return esTipoOponente(valor) ? valor : 'modelo';
}

/** Nivel máximo que admite cada oponente (el modelo llega a 18; Stockfish a 20). */
export function nivelMaximo(oponente: TipoOponente): number {
  return oponente === 'modelo' ? NIVEL_MAX_MODELO : NIVEL_MAX_STOCKFISH;
}

/** Etiqueta del nivel (mismas bandas que usa el backend). */
export function etiquetaDeNivel(nivel: number): string {
  return rangoDeNivel(nivel) ?? '';
}

export {NIVEL_DIAGNOSTICO};
