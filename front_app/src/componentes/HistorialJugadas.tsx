export type CalidadJugada = 'brillante' | 'mejor' | 'error' | 'blunder';

export interface JugadaHistorial {
  san: string;
  calidad?: CalidadJugada;
}

const INSIGNIA: Record<CalidadJugada, {simbolo: string; nombre: string; clase: string}> = {
  brillante: {simbolo: '!!', nombre: 'brillante', clase: 'bg-move-brilliant text-on-secondary-container'},
  mejor: {simbolo: '!', nombre: 'mejor jugada', clase: 'bg-move-best text-on-primary'},
  error: {simbolo: '?', nombre: 'error', clase: 'bg-move-mistake text-on-tertiary-container'},
  blunder: {simbolo: '??', nombre: 'error grave', clase: 'bg-move-blunder text-on-error'},
};

function Celda({jugada}: {jugada?: JugadaHistorial}) {
  if (!jugada) return <span />;
  const insignia = jugada.calidad ? INSIGNIA[jugada.calidad] : null;
  return (
    <span className="flex items-center gap-1.5 font-medium">
      {jugada.san}
      {insignia && (
        <span title={insignia.nombre} aria-label={insignia.nombre} className={`rounded px-1 text-[0.65rem] font-bold ${insignia.clase}`}>
          {insignia.simbolo}
        </span>
      )}
    </span>
  );
}

/** Lista en SAN agrupada por número de jugada (blancas | negras), con insignia de calidad. */
export default function HistorialJugadas({jugadas}: {jugadas: JugadaHistorial[]}) {
  if (jugadas.length === 0) return <p className="text-sm text-on-surface-variant">Aún no hay jugadas.</p>;
  const filas = Array.from({length: Math.ceil(jugadas.length / 2)}, (_, i) => i);
  return (
    <ol aria-label="Historial de jugadas" className="grid grid-cols-[2rem_1fr_1fr] gap-x-2 gap-y-1 text-sm">
      {filas.map((i) => (
        <li key={i} className="col-span-3 grid grid-cols-subgrid items-center rounded-lg px-1 py-0.5 even:bg-surface-low">
          <span className="text-xs text-outline">{i + 1}.</span>
          <Celda jugada={jugadas[i * 2]} />
          <Celda jugada={jugadas[i * 2 + 1]} />
        </li>
      ))}
    </ol>
  );
}
