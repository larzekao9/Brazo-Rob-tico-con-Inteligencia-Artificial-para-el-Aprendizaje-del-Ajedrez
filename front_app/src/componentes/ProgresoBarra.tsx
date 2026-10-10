interface Props {
  /** 0 a 100. */
  valor: number;
  etiqueta?: string;
  tono?: 'primario' | 'cian' | 'ambar';
}

const COLOR: Record<NonNullable<Props['tono']>, string> = {
  primario: 'bg-primary',
  cian: 'bg-secondary',
  ambar: 'bg-tertiary',
};

export default function ProgresoBarra({valor, etiqueta, tono = 'primario'}: Props) {
  const acotado = Math.max(0, Math.min(100, valor));
  return (
    <div>
      {etiqueta && <p className="mb-1 text-xs font-medium text-on-surface-variant">{etiqueta}</p>}
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(acotado)}
        aria-label={etiqueta ?? 'Progreso'}
        className="h-2.5 w-full overflow-hidden rounded-full bg-surface-highest"
      >
        <div className={`h-full rounded-full transition-[width] duration-500 ${COLOR[tono]}`} style={{width: `${acotado}%`}} />
      </div>
    </div>
  );
}
