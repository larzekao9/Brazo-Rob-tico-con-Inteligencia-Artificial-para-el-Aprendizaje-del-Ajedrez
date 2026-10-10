import {rutaImagenPieza} from '../../dominio/ajedrez';
import type {Color} from '../../dominio/tablero';

const OPCIONES = [
  {codigo: 'q', nombre: 'Dama'},
  {codigo: 'r', nombre: 'Torre'},
  {codigo: 'b', nombre: 'Alfil'},
  {codigo: 'n', nombre: 'Caballo'},
] as const;

interface Props {
  color: Color;
  onElegir: (codigo: string) => void;
  onCancelar: () => void;
}

/** Elige en qué pieza se corona el peón (la jugada UCI lleva ese sufijo: e7e8q). */
export default function SelectorPromocion({color, onElegir, onCancelar}: Props) {
  return (
    <div role="dialog" aria-modal="true" aria-label="Elegir pieza de promoción" className="fixed inset-0 z-30 flex items-end justify-center bg-on-surface/40 p-4 sm:items-center">
      <div className="w-full max-w-sm rounded-tarjeta bg-surface-lowest p-4 shadow-xl">
        <h2 className="mb-3 text-center font-titulo text-lg font-bold text-on-surface">Corona tu peón</h2>
        <ul className="grid grid-cols-4 gap-2">
          {OPCIONES.map(({codigo, nombre}) => (
            <li key={codigo}>
              <button
                type="button"
                onClick={() => onElegir(codigo)}
                aria-label={nombre}
                className="flex w-full flex-col items-center gap-1 rounded-boton bg-surface-low p-2 text-xs font-semibold text-on-surface hover:bg-primary-container"
              >
                <img src={rutaImagenPieza(color === 'w' ? codigo.toUpperCase() : codigo)} alt="" className="size-12" />
                {nombre}
              </button>
            </li>
          ))}
        </ul>
        <button type="button" onClick={onCancelar} className="mt-3 w-full rounded-boton py-2 text-sm font-semibold text-on-surface-variant">
          Cancelar
        </button>
      </div>
    </div>
  );
}
