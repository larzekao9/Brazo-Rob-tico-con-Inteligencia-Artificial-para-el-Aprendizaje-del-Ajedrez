import {winPercent} from '../dominio/aprendizaje';

interface Props {
  /** Evaluación en centipeones desde la perspectiva de las blancas. */
  evaluacionCp?: number | null;
  /** Jugadas hasta el mate (positivo: mate a favor de las blancas). */
  mateEn?: number | null;
}

/** Barra horizontal: la parte clara es la ventaja de las blancas, la oscura la de las negras. */
export default function BarraEvaluacion({evaluacionCp = null, mateEn = null}: Props) {
  const sinDatos = evaluacionCp === null && mateEn === null;
  const blancas = sinDatos ? 50 : (winPercent(evaluacionCp ?? 0, mateEn) as number);
  const texto = sinDatos
    ? 'Sin evaluación'
    : mateEn !== null
      ? `Mate en ${Math.abs(mateEn)}`
      : `${(evaluacionCp! / 100 > 0 ? '+' : '') + (evaluacionCp! / 100).toFixed(1)}`;
  return (
    <div role="img" aria-label={`Evaluación: ${texto}. Blancas ${Math.round(blancas)} por ciento.`} className="w-full">
      <div className="flex h-3 w-full overflow-hidden rounded-full border border-outline-variant bg-inverse-surface">
        <div className="h-full bg-surface-lowest transition-[width] duration-500" style={{width: `${blancas}%`}} />
      </div>
      <p className="mt-1 text-right text-xs font-semibold text-on-surface-variant">{texto}</p>
    </div>
  );
}
