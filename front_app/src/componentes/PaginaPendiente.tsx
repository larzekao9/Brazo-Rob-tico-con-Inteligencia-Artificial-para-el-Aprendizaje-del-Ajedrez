import GlassCard from './GlassCard';

/** Contenido temporal de una pantalla que aún no se implementó. */
export default function PaginaPendiente({titulo, ruta}: {titulo: string; ruta: string}) {
  return (
    <section className="flex flex-col gap-4 p-4">
      <h1 className="font-titulo text-2xl font-bold text-on-surface">{titulo}</h1>
      <GlassCard>
        <p className="text-sm text-on-surface-variant">
          Pantalla pendiente de implementar. Ruta: <code>{ruta}</code>
        </p>
      </GlassCard>
    </section>
  );
}
