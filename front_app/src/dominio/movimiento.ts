import {fenAMatriz, piezaEnCasilla} from './ajedrez';

const COLUMNAS = 'abcdefgh';

function aFen(matriz: (string | null)[][]): string {
  return matriz
    .map((fila) => {
      let texto = '';
      let vacias = 0;
      for (const pieza of fila) {
        if (pieza === null) vacias++;
        else {
          if (vacias > 0) texto += vacias;
          vacias = 0;
          texto += pieza;
        }
      }
      return vacias > 0 ? texto + vacias : texto;
    })
    .join('/');
}

/**
 * Posición que se vería tras jugar `uci` (e2e4, e7e8q) sobre `fen`: mueve la pieza, resuelve enroque,
 * captura al paso y promoción, y cambia el turno. SOLO para mostrar la jugada al instante mientras el
 * backend responde: no valida legalidad ni conserva derechos de enroque, y la respuesta real la reemplaza.
 */
export function fenTrasJugada(fen: string, uci: string): string {
  const turno = fen.split(' ')[1];
  const matriz: (string | null)[][] = fenAMatriz(fen);
  const origen = uci.slice(0, 2);
  const destino = uci.slice(2, 4);
  const pieza = piezaEnCasilla(fen, origen);
  if (!pieza) return fen;
  const cOrigen = COLUMNAS.indexOf(origen[0]);
  const fOrigen = 8 - Number(origen[1]);
  const cDestino = COLUMNAS.indexOf(destino[0]);
  const fDestino = 8 - Number(destino[1]);
  const esPeon = pieza.toLowerCase() === 'p';

  // Captura al paso: el peón va en diagonal a una casilla vacía y se lleva el peón de su fila de origen.
  if (esPeon && cOrigen !== cDestino && matriz[fDestino][cDestino] === null) matriz[fOrigen][cDestino] = null;
  // Enroque: el rey salta dos columnas y la torre cruza al otro lado.
  if (pieza.toLowerCase() === 'k' && Math.abs(cDestino - cOrigen) === 2) {
    const corto = cDestino > cOrigen;
    matriz[fOrigen][corto ? 7 : 0] = null;
    matriz[fOrigen][corto ? cDestino - 1 : cDestino + 1] = pieza === 'K' ? 'R' : 'r';
  }
  const promocion = uci[4];
  matriz[fOrigen][cOrigen] = null;
  matriz[fDestino][cDestino] = promocion ? (pieza === pieza.toUpperCase() ? promocion.toUpperCase() : promocion.toLowerCase()) : pieza;

  const nuevoTurno = turno === 'w' ? 'b' : 'w';
  // Se descartan derechos de enroque y casilla al paso: la posición es solo visual.
  return `${aFen(matriz)} ${nuevoTurno} - - 0 1`;
}
