import Chip, {type TonoChip} from '../../componentes/Chip';
import GlassCard from '../../componentes/GlassCard';
import TableroDemo from '../../componentes/TableroDemo';
import {nombreDeCalidad} from './salaUtil';
import type {JugadaAnalisis, MomentoClave} from './tipos';

const TONO_POR_CALIDAD: Record<string, TonoChip> = {
  brillante: 'cian',
  mejor: 'primario',
  imprecision: 'ambar',
  error: 'ambar',
  blunder: 'error',
  colgada_grave: 'error',
};

/** Momentos clave: las jugadas que más ventaja perdieron, cada una con el tablero justo antes de jugarla. */
export default function MomentosClave({momentos, jugadas}: {momentos: MomentoClave[]; jugadas: JugadaAnalisis[]}) {
  if (momentos.length === 0) {
    return <p className="text-sm text-on-surface-variant">No hubo errores relevantes en esta partida.</p>;
  }
  return (
    <ul className="flex flex-col gap-3">
      {momentos.map((momento) => {
        const jugada = jugadas.find((j) => j.numero_ply === momento.ply);
        const bando = momento.color === 'blanco' ? 'blancas' : 'negras';
        return (
          <li key={momento.ply}>
            <GlassCard className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-titulo text-base font-bold text-on-surface">
                  Jugada {Math.ceil(momento.ply / 2)} · {bando}: {momento.jugada_san}
                </span>
                <Chip tono={TONO_POR_CALIDAD[momento.calidad] ?? 'neutro'}>{nombreDeCalidad(momento.calidad)}</Chip>
              </div>
              {jugada && (
                <div className="mx-auto w-full max-w-72">
                  <TableroDemo fen={jugada.fen_antes} orientacion={momento.color === 'blanco' ? 'w' : 'b'} ariaLabel={`Posición antes de ${momento.jugada_san}`} />
                </div>
              )}
              <p className="text-sm text-on-surface-variant">
                Perdió {(momento.perdida_cp / 100).toFixed(1)} peones{momento.mejor_jugada_san && momento.mejor_jugada_san !== momento.jugada_san ? ` · mejor era ${momento.mejor_jugada_san}` : ''}.
              </p>
              {momento.explicacion && <p className="text-sm text-on-surface">{momento.explicacion}</p>}
            </GlassCard>
          </li>
        );
      })}
    </ul>
  );
}
