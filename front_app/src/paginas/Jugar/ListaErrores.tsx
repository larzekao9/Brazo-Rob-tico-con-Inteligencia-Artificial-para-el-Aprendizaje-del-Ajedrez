import {Lightbulb} from 'lucide-react';
import GlassCard from '../../componentes/GlassCard';
import {ESTILO_CATEGORIA} from '../../dominio/aprendizaje';
import type {ErrorDelJugador} from './datosResultado';

/** Puntos a mejorar: las jugadas del jugador que más ventaja costaron, con su explicación. */
export default function ListaErrores({errores, consejo}: {errores: ErrorDelJugador[]; consejo?: string}) {
  return (
    <GlassCard className="flex flex-col gap-3 bg-error-container/40">
      <div className="flex items-center gap-2 text-on-error-container">
        <Lightbulb size={22} aria-hidden="true" />
        <h2 className="font-titulo text-lg font-bold">Puntos a mejorar</h2>
      </div>
      {consejo && <p className="text-sm text-on-surface">{consejo}</p>}
      {errores.length === 0 ? (
        <p className="text-sm text-on-surface-variant">No se detectaron errores importantes en tus jugadas.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {errores.map(({jugada, categoria}) => {
            const estilo = ESTILO_CATEGORIA[categoria as keyof typeof ESTILO_CATEGORIA];
            return (
              <li key={jugada.numero_ply} className="rounded-boton bg-surface-lowest p-3">
                <p className="text-sm font-semibold text-on-surface">
                  Jugada {Math.ceil(jugada.numero_ply / 2)}: {jugada.jugada_san}
                  <span className="ml-2 rounded-full bg-error-container px-2 py-0.5 text-xs font-bold text-on-error-container">{estilo?.etiqueta ?? categoria}</span>
                </p>
                {jugada.mejor_jugada_motor && jugada.mejor_jugada_motor !== jugada.jugada_san && (
                  <p className="text-xs text-on-surface-variant">Mejor era {jugada.mejor_jugada_motor}.</p>
                )}
                {jugada.explicacion && <p className="mt-1 text-sm text-on-surface-variant">{jugada.explicacion}</p>}
              </li>
            );
          })}
        </ul>
      )}
    </GlassCard>
  );
}
