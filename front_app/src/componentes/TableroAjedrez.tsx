import {useEffect, useMemo, useRef, useState} from 'react';
import {turnoDeFen} from '../dominio/ajedrez';
import {
  casillaDelRey,
  casillasParaDibujar,
  colorDePieza,
  imagenDePieza,
  nombreDeColumna,
  partirUci,
  reyEnJaque,
  type Color,
} from '../dominio/tablero';

interface Props {
  fen: string;
  /** Lado que se ve abajo. */
  orientacion?: Color;
  /** Color que mueve el usuario; solo se pueden seleccionar sus piezas. null = tablero sin juego. */
  colorJugador?: Color | null;
  /** Última jugada en UCI ("e2e4") para resaltar origen y destino. */
  ultimaJugada?: string | null;
  /** Pide al backend las casillas destino legales de la pieza tocada. */
  obtenerDestinos?: (casilla: string) => Promise<string[]>;
  /** Se llama al completar el segundo toque (origen -> destino). */
  onMover?: (origen: string, destino: string) => void;
  /** Se llama si falla obtenerDestinos. */
  onError?: (mensaje: string) => void;
  /** Bloquea toques (esperando al rival, partida terminada, jugada en curso). */
  deshabilitado?: boolean;
}

/** Tablero interactivo: se mueve con dos toques (origen, destino), como la app móvil. */
export default function TableroAjedrez({
  fen,
  orientacion = 'w',
  colorJugador = null,
  ultimaJugada = null,
  obtenerDestinos,
  onMover,
  onError,
  deshabilitado = false,
}: Props) {
  const [origen, setOrigen] = useState<string | null>(null);
  const [destinos, setDestinos] = useState<string[]>([]);
  const pedidoActual = useRef(0);

  // Cualquier cambio de posición cancela la selección pendiente.
  useEffect(() => {
    setOrigen(null);
    setDestinos([]);
  }, [fen]);

  const casillas = useMemo(() => casillasParaDibujar(fen, orientacion), [fen, orientacion]);
  const ultima = partirUci(ultimaJugada);
  const turno = turnoDeFen(fen) as Color;
  const reyAmenazado = useMemo(() => (reyEnJaque(fen, turno) ? casillaDelRey(fen, turno) : null), [fen, turno]);

  function limpiar() {
    pedidoActual.current++;
    setOrigen(null);
    setDestinos([]);
  }

  async function seleccionar(casilla: string) {
    const pedido = ++pedidoActual.current;
    setOrigen(casilla);
    setDestinos([]);
    if (!obtenerDestinos) return;
    try {
      const lista = await obtenerDestinos(casilla);
      if (pedido === pedidoActual.current) setDestinos(lista);
    } catch (err) {
      if (pedido !== pedidoActual.current) return;
      limpiar();
      onError?.(err instanceof Error ? err.message : 'No se pudieron calcular las jugadas legales.');
    }
  }

  function alTocar(casilla: string, pieza: string | null) {
    if (deshabilitado || !colorJugador) return;
    const esPropia = pieza !== null && colorDePieza(pieza) === colorJugador;
    if (origen === null) {
      if (esPropia && colorJugador === turno) void seleccionar(casilla);
      return;
    }
    if (casilla === origen) return limpiar();
    if (destinos.includes(casilla)) {
      onMover?.(origen, casilla);
      return limpiar();
    }
    if (esPropia) void seleccionar(casilla);
    else limpiar();
  }

  return (
    <div role="grid" aria-label="Tablero de ajedrez" className="grid aspect-square w-full grid-cols-8 overflow-hidden rounded-2xl border-2 border-outline-variant shadow-lg shadow-on-surface/10">
      {casillas.map(({casilla, clara, pieza, columna, fila}, indice) => {
        const esOrigen = casilla === origen;
        const esDestino = destinos.includes(casilla);
        const esUltima = ultima !== null && (casilla === ultima.origen || casilla === ultima.destino);
        const esJaque = casilla === reyAmenazado;
        const descripcion = `${casilla}, ${pieza ? `pieza ${pieza}` : 'vacía'}${esOrigen ? ', seleccionada' : ''}${esDestino ? ', jugada legal' : ''}${esJaque ? ', rey en jaque' : ''}`;
        const mostrarFila = indice % 8 === 0;
        const mostrarColumna = indice >= 56;
        return (
          <button
            key={casilla}
            type="button"
            role="gridcell"
            aria-label={descripcion}
            aria-selected={esOrigen}
            disabled={deshabilitado || !colorJugador}
            onClick={() => alTocar(casilla, pieza)}
            className={`relative flex aspect-square items-center justify-center p-0 disabled:cursor-default ${clara ? 'bg-board-light' : 'bg-board-dark'}`}
          >
            {esUltima && <span className="absolute inset-0 bg-board-last-move" aria-hidden="true" />}
            {esJaque && <span className="absolute inset-0 bg-board-check" aria-hidden="true" />}
            {esOrigen && <span className="absolute inset-0 bg-board-highlight ring-4 ring-inset ring-primary" aria-hidden="true" />}
            {pieza && <img src={imagenDePieza(pieza)} alt="" draggable={false} className="relative size-[88%] select-none" />}
            {esDestino && !pieza && <span className="absolute size-[28%] rounded-full bg-primary/70" aria-hidden="true" />}
            {esDestino && pieza && <span className="absolute inset-[6%] rounded-full border-4 border-primary/85" aria-hidden="true" />}
            {mostrarFila && (
              <span className="pointer-events-none absolute left-0.5 top-0 text-[0.6rem] font-bold text-on-surface-variant/70" aria-hidden="true">
                {8 - fila}
              </span>
            )}
            {mostrarColumna && (
              <span className="pointer-events-none absolute bottom-0 right-0.5 text-[0.6rem] font-bold text-on-surface-variant/70" aria-hidden="true">
                {nombreDeColumna(columna)}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
