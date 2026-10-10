interface Props {
  /** Evaluación por jugada en centipeones (perspectiva blancas). Los mates se pasan acotados. */
  evaluaciones: number[];
  /** Tope vertical en centipeones (se recorta a +-tope). */
  tope?: number;
}

const ANCHO = 300;
const ALTO = 120;

/** Curva de evaluación de la partida, SVG propio sin librería de gráficos. */
export default function GraficoEvaluacion({evaluaciones, tope = 800}: Props) {
  if (evaluaciones.length < 2) {
    return <p className="text-sm text-on-surface-variant">No hay suficientes jugadas para dibujar la curva.</p>;
  }
  const x = (i: number) => (i / (evaluaciones.length - 1)) * ANCHO;
  const y = (cp: number) => ALTO / 2 - (Math.max(-tope, Math.min(tope, cp)) / tope) * (ALTO / 2 - 4);
  const puntos = evaluaciones.map((cp, i) => `${x(i).toFixed(1)},${y(cp).toFixed(1)}`).join(' ');
  const area = `0,${ALTO / 2} ${puntos} ${ANCHO},${ALTO / 2}`;
  return (
    <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img" aria-label="Curva de evaluación de la partida" className="h-auto w-full overflow-visible">
      <rect x="0" y="0" width={ANCHO} height={ALTO} rx="12" className="fill-surface-low" />
      <polygon points={area} className="fill-primary/20" />
      <line x1="0" y1={ALTO / 2} x2={ANCHO} y2={ALTO / 2} className="stroke-outline-variant" strokeDasharray="4 4" />
      <polyline points={puntos} fill="none" className="stroke-primary" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
