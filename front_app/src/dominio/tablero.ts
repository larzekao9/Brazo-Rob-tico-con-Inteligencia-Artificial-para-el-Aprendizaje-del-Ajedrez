import {fenAMatriz, nombreCasilla, rutaImagenPieza} from './ajedrez';

export type Color = 'w' | 'b';

export interface CasillaVista {
  casilla: string;
  /** Casilla clara (según el tablero, no según la orientación). */
  clara: boolean;
  /** Letra FEN de la pieza (P, n, K...) o null. */
  pieza: string | null;
  fila: number;
  columna: number;
}

/** Las 64 casillas en el orden en que se dibujan (arriba-izquierda primero), según la orientación. */
export function casillasParaDibujar(fen: string, orientacion: Color): CasillaVista[] {
  const matriz: (string | null)[][] = fenAMatriz(fen);
  const lista: CasillaVista[] = [];
  for (let f = 0; f < 8; f++) {
    for (let c = 0; c < 8; c++) {
      const fila = orientacion === 'w' ? f : 7 - f;
      const columna = orientacion === 'w' ? c : 7 - c;
      lista.push({
        casilla: nombreCasilla(fila, columna),
        clara: (fila + columna) % 2 === 0,
        pieza: matriz[fila]?.[columna] ?? null,
        fila,
        columna,
      });
    }
  }
  return lista;
}

export function imagenDePieza(pieza: string): string {
  return rutaImagenPieza(pieza);
}

export function colorDePieza(pieza: string): Color {
  return pieza === pieza.toUpperCase() ? 'w' : 'b';
}

/** "e2e4" o "e7e8q" -> {origen: "e2", destino: "e4"}; null si no es UCI. */
export function partirUci(uci: string | null | undefined): {origen: string; destino: string} | null {
  if (!uci || !/^[a-h][1-8][a-h][1-8][qrbn]?$/i.test(uci)) return null;
  return {origen: uci.slice(0, 2), destino: uci.slice(2, 4)};
}

export function nombreDeColumna(columna: number): string {
  return 'abcdefgh'[columna];
}

const SALTOS_CABALLO = [[-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1]];
const DIAGONALES = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
const RECTAS = [[-1, 0], [1, 0], [0, -1], [0, 1]];

/** Casilla del rey del color dado, o null si no está en el FEN. */
export function casillaDelRey(fen: string, color: Color): string | null {
  const rey = color === 'w' ? 'K' : 'k';
  const matriz: (string | null)[][] = fenAMatriz(fen);
  for (let f = 0; f < 8; f++) {
    for (let c = 0; c < 8; c++) if (matriz[f][c] === rey) return nombreCasilla(f, c);
  }
  return null;
}

/** Si el rey del color indicado está atacado en el FEN (solo geometría, sin generar jugadas). */
export function reyEnJaque(fen: string, color: Color): boolean {
  const matriz: (string | null)[][] = fenAMatriz(fen);
  const rey = color === 'w' ? 'K' : 'k';
  let fr = -1;
  let cr = -1;
  matriz.forEach((fila, f) => fila.forEach((p, c) => { if (p === rey) { fr = f; cr = c; } }));
  if (fr < 0) return false;
  const enemigo = (p: string | null, tipos: string) =>
    p !== null && colorDePieza(p) !== color && tipos.includes(p.toLowerCase());
  const en = (f: number, c: number) => (f >= 0 && f < 8 && c >= 0 && c < 8 ? matriz[f][c] : null);

  if (SALTOS_CABALLO.some(([df, dc]) => enemigo(en(fr + df, cr + dc), 'n'))) return true;
  // Peón enemigo: las negras atacan hacia abajo del tablero (fila+1), las blancas hacia arriba.
  const dirPeon = color === 'w' ? -1 : 1;
  if ([-1, 1].some((dc) => enemigo(en(fr + dirPeon, cr + dc), 'p'))) return true;
  if ([...DIAGONALES, ...RECTAS].some(([df, dc]) => enemigo(en(fr + df, cr + dc), 'k'))) return true;
  const barrer = (dirs: number[][], tipos: string) =>
    dirs.some(([df, dc]) => {
      for (let d = 1; d < 8; d++) {
        const p = en(fr + df * d, cr + dc * d);
        if (p === null && fr + df * d >= 0 && fr + df * d < 8 && cr + dc * d >= 0 && cr + dc * d < 8) continue;
        return enemigo(p, tipos);
      }
      return false;
    });
  return barrer(DIAGONALES, 'bq') || barrer(RECTAS, 'rq');
}
