import {BookOpen, Flag, Lock, Puzzle} from 'lucide-react';
import type {ComponentType} from 'react';

export interface Insignia {
  id: string;
  titulo: string;
  desbloqueada: boolean;
  Icono: ComponentType<{size?: number; 'aria-hidden'?: boolean}>;
}

/** Insignias con datos reales de la cuenta; nada de progreso inventado. */
export function calcularInsignias(opts: {totalPartidas: number; piezasVistas: number; repasada: boolean; mostrarPiezas: boolean}): Insignia[] {
  const todas: Insignia[] = [
    {id: 'primera-partida', titulo: 'Primera partida jugada', desbloqueada: opts.totalPartidas > 0, Icono: Flag},
    {id: 'seis-piezas', titulo: `Conoce las 6 piezas: ${opts.piezasVistas}/6`, desbloqueada: opts.piezasVistas >= 6, Icono: Puzzle},
    {id: 'repaso-turing', titulo: 'Repasaste una partida con Turing', desbloqueada: opts.repasada, Icono: BookOpen},
  ];
  // La insignia de las 6 piezas sigue el mismo criterio que el camino: solo para principiantes.
  return opts.mostrarPiezas ? todas : todas.filter((i) => i.id !== 'seis-piezas');
}

export default function Logros({insignias, cargando}: {insignias: Insignia[]; cargando: boolean}) {
  return (
    <>
      <ul className="grid grid-cols-2 gap-2">
        {insignias.map(({id, titulo, desbloqueada, Icono}) => (
          <li
            key={id}
            className={`flex flex-col items-center gap-2 rounded-2xl border p-3 text-center ${
              desbloqueada ? 'border-primary bg-primary-container text-on-primary-container' : 'border-outline-variant bg-surface-low text-on-surface-variant'
            }`}
          >
            {desbloqueada ? <Icono size={26} aria-hidden /> : <Lock size={26} aria-hidden />}
            <span className="text-sm font-semibold">{titulo}</span>
            <span className="text-[10px] font-bold uppercase tracking-wide">{desbloqueada ? 'Desbloqueada' : 'Todavía no'}</span>
          </li>
        ))}
      </ul>
      {cargando && <p className="text-xs text-on-surface-variant">Revisando si ya repasaste una partida…</p>}
    </>
  );
}
