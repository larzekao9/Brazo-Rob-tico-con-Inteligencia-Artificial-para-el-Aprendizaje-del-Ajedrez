import {precisionAPorcentaje} from '../../../dominio/nivelJugador';

export interface Calibracion {
  partida_id?: string;
  precision: number;
  nivel?: number;
}

const ANCHO = 340;
const ALTO = 176;
const MARGEN = {izq: 30, der: 14, arriba: 20, abajo: 38};

/**
 * Gráfica de líneas (SVG, sin librerías) con la precisión de las últimas calibraciones. Eje Y fijo 0-100;
 * cada punto lleva su valor arriba y, abajo, el número de partida (P) y el nivel que quedó tras ella (N).
 */
export default function GraficaPrecision({calibraciones, partidasCalibradas}: {calibraciones?: Calibracion[]; partidasCalibradas: number}) {
  const puntos = (Array.isArray(calibraciones) ? calibraciones : [])
    .map((c) => ({...c, pct: precisionAPorcentaje(c?.precision)}))
    .filter((c): c is typeof c & {pct: number} => c.pct != null);

  if (puntos.length === 0) return <p className="text-xs text-on-surface-variant">Todavía no hay partidas medidas para graficar.</p>;

  const anchoUtil = ANCHO - MARGEN.izq - MARGEN.der;
  const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
  const posX = (i: number) => (puntos.length === 1 ? MARGEN.izq + anchoUtil / 2 : MARGEN.izq + (i / (puntos.length - 1)) * anchoUtil);
  const posY = (v: number) => MARGEN.arriba + (1 - v / 100) * altoUtil;
  const primera = Math.max(1, (partidasCalibradas || puntos.length) - puntos.length + 1);
  const trazado = puntos.map((p, i) => `${i === 0 ? 'M' : 'L'} ${posX(i)} ${posY(p.pct)}`).join(' ');
  const descripcion = `Precisión por partida: ${puntos.map((p, i) => `partida ${primera + i}, ${p.pct} %`).join('; ')}.`;

  return (
    <div className="rounded-2xl bg-surface-low p-3">
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img" aria-label={descripcion} className="mx-auto h-auto w-full max-w-md">
        {[0, 50, 100].map((marca) => (
          <g key={marca}>
            <line x1={MARGEN.izq} x2={ANCHO - MARGEN.der} y1={posY(marca)} y2={posY(marca)} className="stroke-outline-variant" strokeDasharray={marca === 0 ? undefined : '3 3'} />
            <text x={MARGEN.izq - 6} y={posY(marca) + 3} textAnchor="end" className="fill-on-surface-variant text-[10px]">
              {marca}
            </text>
          </g>
        ))}
        {puntos.length > 1 && <path d={trazado} fill="none" className="stroke-primary" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />}
        {puntos.map((p, i) => (
          <g key={`${p.partida_id ?? 'p'}-${i}`}>
            <circle cx={posX(i)} cy={posY(p.pct)} r={i === puntos.length - 1 ? 5 : 3.5} className="fill-primary stroke-surface-lowest" strokeWidth={1.5} />
            <text x={posX(i)} y={posY(p.pct) - 9} textAnchor="middle" className="fill-on-surface text-[10px] font-semibold">
              {p.pct}
            </text>
            <text x={posX(i)} y={ALTO - 22} textAnchor="middle" className="fill-on-surface-variant text-[10px]">
              P{primera + i}
            </text>
            {typeof p.nivel === 'number' && (
              <text x={posX(i)} y={ALTO - 9} textAnchor="middle" className="fill-outline text-[10px]">
                N{p.nivel}
              </text>
            )}
          </g>
        ))}
      </svg>
      <p className="text-center text-xs text-outline">P = número de partida · N = nivel tras esa partida · eje: precisión (%)</p>
    </div>
  );
}
