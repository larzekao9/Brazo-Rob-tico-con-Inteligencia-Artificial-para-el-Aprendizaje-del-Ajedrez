import {useMemo} from 'react';
import {casillasParaDibujar, imagenDePieza, type Color} from '../dominio/tablero';

interface Props {
  fen: string;
  orientacion?: Color;
  /** Casillas (p. ej. "e4") donde se dibuja un punto de movimiento legal ilustrativo. */
  destinos?: string[];
  /** Casillas a resaltar (p. ej. una fila, columna o la pieza explicada). */
  resaltadas?: string[];
  ariaLabel?: string;
}

/** Tablero de solo lectura para las lecciones: sin toques, con puntos de movimientos legales. */
export default function TableroDemo({fen, orientacion = 'w', destinos = [], resaltadas = [], ariaLabel = 'Tablero de ajedrez ilustrativo'}: Props) {
  const casillas = useMemo(() => casillasParaDibujar(fen, orientacion), [fen, orientacion]);
  return (
    <div role="img" aria-label={ariaLabel} className="grid aspect-square w-full grid-cols-8 overflow-hidden rounded-2xl border-2 border-outline-variant shadow-md shadow-on-surface/10">
      {casillas.map(({casilla, clara, pieza}) => (
        <div key={casilla} className={`relative flex aspect-square items-center justify-center ${clara ? 'bg-board-light' : 'bg-board-dark'}`}>
          {resaltadas.includes(casilla) && <span className="absolute inset-0 bg-board-highlight" aria-hidden="true" />}
          {pieza && <img src={imagenDePieza(pieza)} alt="" draggable={false} className="relative size-[88%] select-none" />}
          {destinos.includes(casilla) && <span className="absolute size-[28%] rounded-full bg-primary/70" aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}
