export default function Cargando({mensaje = 'Cargando…'}: {mensaje?: string}) {
  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center justify-center gap-3 py-10 text-on-surface-variant">
      <span className="size-8 animate-spin rounded-full border-4 border-surface-highest border-t-primary" aria-hidden="true" />
      <span className="text-sm">{mensaje}</span>
    </div>
  );
}
