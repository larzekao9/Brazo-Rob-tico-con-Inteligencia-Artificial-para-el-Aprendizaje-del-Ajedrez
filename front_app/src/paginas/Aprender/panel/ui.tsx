import type {ReactNode} from 'react';

/** Indicador de carga compacto para dentro de una sección. */
export function CargandoInline({texto}: {texto: string}) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 py-2 text-sm text-on-surface-variant">
      <span className="size-4 animate-spin rounded-full border-2 border-surface-highest border-t-primary motion-reduce:animate-none" aria-hidden="true" />
      {texto}
    </div>
  );
}

/** Texto de estado vacío ("todavía no jugaste…"). */
export function Vacio({children}: {children: ReactNode}) {
  return <p className="rounded-2xl bg-surface-low p-3 text-sm text-on-surface-variant">{children}</p>;
}

/** Clase de tamaño del texto de explicación según la preferencia "Lectura fácil". */
export function claseTexto(lecturaFacil: boolean): string {
  return lecturaFacil ? 'text-lg leading-relaxed' : 'text-sm leading-relaxed';
}
