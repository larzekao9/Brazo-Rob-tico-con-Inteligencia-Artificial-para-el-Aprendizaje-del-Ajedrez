import type {HTMLAttributes, ReactNode} from 'react';

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** Relleno interno; 'ninguno' deja el contenido a ras del borde. */
  relleno?: 'normal' | 'ninguno';
}

/** Tarjeta translúcida (equivale a glass_card.dart). */
export default function GlassCard({children, relleno = 'normal', className = '', ...resto}: Props) {
  return (
    <div
      {...resto}
      className={`rounded-tarjeta border border-glass-border bg-glass shadow-lg shadow-on-surface/5 backdrop-blur-md ${
        relleno === 'normal' ? 'p-4' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}
