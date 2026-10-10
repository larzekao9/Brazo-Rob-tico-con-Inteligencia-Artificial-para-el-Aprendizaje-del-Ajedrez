interface Props {
  /** Segundos restantes. */
  segundos: number;
  etiqueta: string;
  activo?: boolean;
  /** Por debajo de este valor el reloj se marca como poco tiempo. */
  umbralPocoTiempo?: number;
}

export function formatearReloj(segundos: number): string {
  const total = Math.max(0, Math.floor(segundos));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function RelojAjedrez({segundos, etiqueta, activo = false, umbralPocoTiempo = 30}: Props) {
  const poco = segundos <= umbralPocoTiempo;
  const estilo = poco
    ? 'bg-clock-low-bg text-clock-low-text border-tertiary'
    : activo
      ? 'bg-surface-lowest text-on-surface border-clock-active'
      : 'bg-surface-low text-on-surface-variant border-transparent';
  return (
    <div
      role="timer"
      aria-label={`${etiqueta}: ${formatearReloj(segundos)}${activo ? ', en juego' : ''}${poco ? ', poco tiempo' : ''}`}
      className={`flex items-center justify-between gap-3 rounded-boton border-2 px-4 py-2 ${estilo}`}
    >
      <span className="text-xs font-semibold">{etiqueta}{activo ? ' · turno' : ''}</span>
      <span className="font-titulo text-xl font-bold tabular-nums">{formatearReloj(segundos)}</span>
    </div>
  );
}
