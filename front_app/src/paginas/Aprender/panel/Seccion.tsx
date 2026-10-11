import {ChevronDown} from 'lucide-react';
import type {ReactNode} from 'react';
import GlassCard from '../../../componentes/GlassCard';

interface Props {
  id: string;
  titulo: string;
  icono: ReactNode;
  abierta: boolean;
  onAlternar(): void;
  children: ReactNode;
}

/** Tarjeta tipo acordeón: el contenido solo se monta cuando está abierta, así cada sección pide sus datos al abrirse. */
export default function Seccion({id, titulo, icono, abierta, onAlternar, children}: Props) {
  return (
    <GlassCard relleno="ninguno" id={`seccion-${id}`} className="scroll-mt-20 overflow-hidden">
      <button
        type="button"
        onClick={onAlternar}
        aria-expanded={abierta}
        aria-controls={`contenido-${id}`}
        className="flex min-h-14 w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-container text-primary" aria-hidden="true">
            {icono}
          </span>
          <span className="truncate font-titulo text-base font-bold text-on-surface">{titulo}</span>
        </span>
        <ChevronDown
          size={20}
          aria-hidden="true"
          className={`shrink-0 text-on-surface-variant transition-transform motion-reduce:transition-none ${abierta ? 'rotate-180' : ''}`}
        />
      </button>
      {abierta && (
        <div id={`contenido-${id}`} className="flex flex-col gap-3 border-t border-outline-variant px-4 pb-4 pt-3">
          {children}
        </div>
      )}
    </GlassCard>
  );
}
