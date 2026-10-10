export interface EjeRadar {
  nombre: string;
  /** 0 a 100. */
  valor: number;
}

const TAM = 220;
const CENTRO = TAM / 2;
const RADIO = 78;

function punto(indice: number, total: number, escala: number): [number, number] {
  const angulo = -Math.PI / 2 + (indice * 2 * Math.PI) / total;
  return [CENTRO + Math.cos(angulo) * RADIO * escala, CENTRO + Math.sin(angulo) * RADIO * escala];
}

const comoPuntos = (pares: [number, number][]) => pares.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(' ');

/** Mapa de habilidades: radar de N ejes (5 en el Inicio), SVG propio. */
export default function RadarHabilidades({ejes}: {ejes: EjeRadar[]}) {
  const n = ejes.length;
  if (n < 3) return null;
  const poligono = comoPuntos(ejes.map((e, i) => punto(i, n, Math.max(0, Math.min(100, e.valor)) / 100)));
  const resumen = ejes.map((e) => `${e.nombre} ${Math.round(e.valor)}`).join(', ');
  return (
    <svg viewBox={`0 0 ${TAM} ${TAM}`} role="img" aria-label={`Mapa de habilidades: ${resumen}`} className="mx-auto h-auto w-full max-w-72">
      {[0.25, 0.5, 0.75, 1].map((escala) => (
        <polygon key={escala} points={comoPuntos(ejes.map((_, i) => punto(i, n, escala)))} fill="none" className="stroke-outline-variant" strokeWidth="1" />
      ))}
      {ejes.map((_, i) => {
        const [px, py] = punto(i, n, 1);
        return <line key={i} x1={CENTRO} y1={CENTRO} x2={px} y2={py} className="stroke-outline-variant" strokeWidth="1" />;
      })}
      <polygon points={poligono} className="fill-primary/25 stroke-primary" strokeWidth="2.5" strokeLinejoin="round" />
      {ejes.map((eje, i) => {
        const [px, py] = punto(i, n, 1.2);
        return (
          <text key={eje.nombre} x={px} y={py} textAnchor="middle" dominantBaseline="middle" className="fill-on-surface-variant text-[9px] font-semibold">
            {eje.nombre}
          </text>
        );
      })}
    </svg>
  );
}
