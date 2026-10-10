import type {ButtonHTMLAttributes, ReactNode} from 'react';

type Variante = 'primario' | 'secundario' | 'peligro';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variante?: Variante;
  /** Mientras es true el botón queda deshabilitado y muestra `textoCargando`. */
  cargando?: boolean;
  textoCargando?: string;
  anchoCompleto?: boolean;
}

const ESTILOS: Record<Variante, string> = {
  primario: 'bg-primary text-on-primary shadow-md shadow-primary/30 hover:bg-on-primary-fixed-variant',
  secundario: 'bg-surface-lowest text-primary border border-outline-variant hover:bg-primary-container',
  peligro: 'bg-error text-on-error hover:bg-on-error-container',
};

export default function BotonPrimario({
  children,
  variante = 'primario',
  cargando = false,
  textoCargando = 'Cargando…',
  anchoCompleto = true,
  disabled,
  className = '',
  type = 'button',
  ...resto
}: Props) {
  return (
    <button
      {...resto}
      type={type}
      disabled={disabled || cargando}
      aria-busy={cargando}
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-boton px-5 py-3 font-titulo text-base font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        ESTILOS[variante]
      } ${anchoCompleto ? 'w-full' : ''} ${className}`}
    >
      {cargando ? textoCargando : children}
    </button>
  );
}
