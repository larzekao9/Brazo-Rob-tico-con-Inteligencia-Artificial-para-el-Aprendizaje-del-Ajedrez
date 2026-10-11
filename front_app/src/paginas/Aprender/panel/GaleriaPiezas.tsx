import {useMemo, useState} from 'react';
import {Check, Zap} from 'lucide-react';
import BotonPrimario from '../../../componentes/BotonPrimario';
import {casillasIlustrativas, rutaImagenPieza} from '../../../dominio/ajedrez';
import {PIEZAS} from '../../../dominio/contenido/piezas';
import {irA} from '../../../router';

interface Pieza {
  tipo: string;
  nombre: string;
  articulo: string;
  letra: string;
  apodo: string;
  comoSeMueve: string;
  reglaEspecial: string;
}

const FILA_CENTRO = 3;
const COLUMNA_CENTRO = 3;

/** Tablero 8x8 ilustrativo: la pieza sola en el centro y sus casillas de movimiento (no es una posición real). */
function MiniTablero({pieza}: {pieza: Pieza}) {
  const destinos = useMemo(() => casillasIlustrativas(pieza.tipo, FILA_CENTRO, COLUMNA_CENTRO) as [number, number][], [pieza.tipo]);
  return (
    <div
      role="img"
      aria-label={`Tablero vacío que muestra hacia dónde se mueve ${pieza.articulo} ${pieza.nombre.toLowerCase()} desde el centro (ilustrativo, no es una posición real)`}
      className="mx-auto grid aspect-square w-full max-w-xs grid-cols-8 grid-rows-8 overflow-hidden rounded-xl border border-outline-variant"
    >
      {Array.from({length: 64}, (_, i) => {
        const fila = Math.floor(i / 8);
        const columna = i % 8;
        const esCentro = fila === FILA_CENTRO && columna === COLUMNA_CENTRO;
        const esDestino = !esCentro && destinos.some(([f, c]) => f === fila && c === columna);
        return (
          <div key={i} className={`relative flex items-center justify-center ${(fila + columna) % 2 === 0 ? 'bg-board-light' : 'bg-board-dark'} ${esCentro ? 'bg-board-highlight' : ''}`}>
            {esCentro && <img src={rutaImagenPieza(pieza.letra)} alt="" draggable={false} className="size-[85%]" />}
            {esDestino && <span className="size-1/3 rounded-full bg-primary" aria-hidden="true" />}
          </div>
        );
      })}
    </div>
  );
}

interface Props {
  vistas: string[];
  onVer(tipo: string): void;
  clase: string;
}

/** Galería de las 6 piezas: al tocar una se ve su apodo, cómo se mueve (mini-tablero) y su regla especial. */
export default function GaleriaPiezas({vistas, onVer, clase}: Props) {
  const [elegida, setElegida] = useState<string | null>(null);
  const piezas = PIEZAS as Pieza[];
  const actual = piezas.find((p) => p.tipo === elegida) ?? null;

  const elegir = (tipo: string) => {
    setElegida(tipo);
    onVer(tipo);
  };

  return (
    <>
      <p className="text-sm text-on-surface-variant">
        Conociste {vistas.length} de {piezas.length} piezas. Toca una para ver cómo se mueve.
      </p>
      <div className="grid grid-cols-3 gap-2">
        {piezas.map((p) => {
          const activa = p.tipo === elegida;
          return (
            <button
              key={p.tipo}
              type="button"
              onClick={() => elegir(p.tipo)}
              aria-pressed={activa}
              className={`relative flex min-h-20 flex-col items-center justify-center gap-1 rounded-2xl border py-2 text-xs font-semibold ${
                activa ? 'border-primary bg-primary-container text-on-primary-container' : 'border-outline-variant bg-surface-lowest text-on-surface-variant'
              }`}
            >
              {vistas.includes(p.tipo) && <Check size={12} className="absolute right-1.5 top-1.5 text-primary" aria-label="Ya la viste" />}
              <img src={rutaImagenPieza(p.letra)} alt="" draggable={false} className="size-9" />
              {p.nombre}
            </button>
          );
        })}
      </div>

      {actual && (
        <div className="flex flex-col gap-3">
          <p className={`${clase} font-semibold italic text-primary`}>“{actual.apodo}”</p>
          <p className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
            Cómo se mueve {actual.articulo} {actual.nombre.toLowerCase()}
          </p>
          <MiniTablero pieza={actual} />
          <p className={`${clase} text-on-surface`}>{actual.comoSeMueve}</p>
          <p className={`flex items-start gap-2 rounded-xl bg-tertiary-container p-3 text-on-tertiary-container ${clase}`}>
            <Zap size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              <strong>Dato clave:</strong> {actual.reglaEspecial}
            </span>
          </p>
        </div>
      )}

      <BotonPrimario variante="secundario" onClick={() => irA('/aprender/piezas')}>
        Ver las tarjetas de piezas
      </BotonPrimario>
    </>
  );
}
