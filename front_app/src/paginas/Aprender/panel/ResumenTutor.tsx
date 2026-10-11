import {Lightbulb, Timer, TrendingUp} from 'lucide-react';
import ErrorReintentar from '../../../componentes/ErrorReintentar';
import {formatearDuracion} from '../../../dominio/formatoTiempo';
import type {UltimaPartida} from './useUltimaPartida';
import {CargandoInline, Vacio} from './ui';

/** Precisión y consejo del tutor para la última partida analizada. */
export default function ResumenTutor({datos, clase}: {datos: UltimaPartida; clase: string}) {
  const {cargandoHistorial, errorHistorial, ultima, analisis, analizando, errorAnalisis} = datos;

  if (cargandoHistorial) return <CargandoInline texto="Buscando tu última partida…" />;
  if (errorHistorial) return <ErrorReintentar mensaje={errorHistorial.message || 'No se pudo cargar tu historial de partidas.'} onReintentar={datos.reintentarHistorial} />;
  if (!ultima) return <Vacio>Juega una partida para que Turing te arme un resumen con consejos.</Vacio>;
  if (analizando) return <CargandoInline texto="Armando tu resumen…" />;
  if (errorAnalisis) return <ErrorReintentar mensaje={errorAnalisis.message || 'No se pudo armar el resumen de tu partida.'} onReintentar={datos.reintentarAnalisis} />;
  if (!analisis) return null;

  const {resumen} = analisis;
  const precision = resumen.precision_jugador ?? resumen.precision_global;
  return (
    <>
      <p className="flex items-center gap-2 font-titulo text-base font-bold text-on-secondary-fixed-variant">
        <TrendingUp size={20} aria-hidden="true" />
        {precision.toFixed(0)}% de precisión en tus jugadas de la última partida
      </p>
      {resumen.tiempo_medio_jugador_ms != null && (
        <p className="flex items-center gap-2 text-xs text-on-surface-variant">
          <Timer size={14} aria-hidden="true" />
          Partida de {formatearDuracion(resumen.duracion_ms)} · pensaste en promedio {formatearDuracion(resumen.tiempo_medio_jugador_ms)} por jugada
        </p>
      )}
      {resumen.consejo_tutor && (
        <div className="flex flex-col gap-1 rounded-xl bg-surface-low p-3">
          <span className="flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-primary">
            <Lightbulb size={14} aria-hidden="true" />
            Consejo de Turing
          </span>
          <p className={`${clase} text-on-surface`}>{resumen.consejo_tutor}</p>
        </div>
      )}
    </>
  );
}
