import type {ReactNode} from 'react';

export type TonoChip = 'neutro' | 'primario' | 'cian' | 'ambar' | 'error';

const TONOS: Record<TonoChip, string> = {
  neutro: 'bg-surface-highest text-on-surface-variant',
  primario: 'bg-primary-container text-on-primary-container',
  cian: 'bg-secondary-container text-on-secondary-container',
  ambar: 'bg-tertiary-container text-on-tertiary-container',
  error: 'bg-error-container text-on-error-container',
};

/** Etiqueta pequeña (nivel, rango, estado). El significado va en el texto, no solo en el color. */
export default function Chip({children, tono = 'neutro', icono}: {children: ReactNode; tono?: TonoChip; icono?: ReactNode}) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${TONOS[tono]}`}>
      {icono}
      {children}
    </span>
  );
}
