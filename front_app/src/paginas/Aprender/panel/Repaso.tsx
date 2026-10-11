import {useMemo, useState} from 'react';
import {Bot, Brain, Info, RotateCcw, Timer, Volume2, VolumeX} from 'lucide-react';
import {clasificarJugada, esDelJugador, notaDeTiempoDeJugada} from '../../../dominio/aprendizaje';
import {fechaHoraLegible, formatearDuracion} from '../../../dominio/formatoTiempo';
import ErrorReintentar from '../../../componentes/ErrorReintentar';
import {jugadasParaRepasar, NOMBRE_PRINCIPIO, terminosDeJugada} from './glosario';
import type {JugadaAnalisis, UltimaPartida} from './useUltimaPartida';
import {CargandoInline, Vacio} from './ui';
import type {Narracion} from './voz';

const ESTILO_CALIDAD: Record<string, {etiqueta: string; clase: string}> = {
  brillante: {etiqueta: 'Brillante', clase: 'bg-secondary-container text-on-secondary-container'},
  mejor: {etiqueta: 'Mejor jugada', clase: 'bg-primary-container text-on-primary-container'},
  excelente: {etiqueta: 'Excelente', clase: 'bg-primary-container text-on-primary-container'},
  buena: {etiqueta: 'Buena', clase: 'bg-surface-container text-on-surface-variant'},
  imprecision: {etiqueta: 'Imprecisión', clase: 'bg-tertiary-container text-on-tertiary-container'},
  error: {etiqueta: 'Error', clase: 'bg-tertiary-container text-on-tertiary-container'},
  blunder: {etiqueta: 'Blunder', clase: 'bg-error-container text-on-error-container'},
};

export function textoNarrableDeJugada(jugada: JugadaAnalisis): string {
  return `Jugada ${jugada.numero_ply}, ${jugada.jugada_san}. ${jugada.explicacion}`;
}

/** Las jugadas que se repasan de una partida analizada (solo las del jugador, nunca las de Turing o Stockfish). */
export function tarjetasDeRepaso(jugadas: JugadaAnalisis[] | undefined): JugadaAnalisis[] {
  return jugadasParaRepasar((jugadas ?? []).filter(esDelJugador));
}

function TarjetaJugada({jugada, tiempoMedioMs, clase, voz}: {jugada: JugadaAnalisis; tiempoMedioMs?: number | null; clase: string; voz: Narracion}) {
  const [abierto, setAbierto] = useState<string | null>(null);
  const estilo = ESTILO_CALIDAD[jugada.calidad] ?? ESTILO_CALIDAD.buena;
  const terminos = terminosDeJugada(jugada.principio_ajedrecistico);
  const nota = notaDeTiempoDeJugada(jugada, clasificarJugada(jugada), tiempoMedioMs);
  const definicion = terminos.find((t) => t.termino === abierto)?.definicion;

  const alternarVoz = () => (voz.narrando ? voz.detener() : voz.narrar(textoNarrableDeJugada(jugada)));

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-outline-variant bg-surface-lowest p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${estilo.clase}`}>{estilo.etiqueta}</span>
        <span className="text-xs font-semibold text-on-surface-variant">
          Jugada {jugada.numero_ply} · {jugada.jugada_san}
        </span>
        {jugada.tiempo_ms != null && (
          <span className="flex items-center gap-1 text-xs text-on-surface-variant">
            <Timer size={12} aria-hidden="true" />
            Tardaste {formatearDuracion(jugada.tiempo_ms)}
          </span>
        )}
      </div>
      {nota && <p className={`${clase} text-on-surface-variant`}>{nota}</p>}

      <div className="flex flex-col gap-1 rounded-xl bg-surface-low p-3">
        <span className="text-xs font-bold uppercase tracking-wide text-primary">
          {NOMBRE_PRINCIPIO[jugada.principio_ajedrecistico ?? ''] ?? NOMBRE_PRINCIPIO.general}
        </span>
        <p className={`${clase} text-on-surface`}>{jugada.explicacion}</p>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold text-on-surface-variant">Términos de esta jugada (toca uno para ver qué significa)</span>
        <div className="flex flex-wrap gap-2">
          {terminos.map((t) => (
            <button
              key={t.termino}
              type="button"
              aria-expanded={abierto === t.termino}
              onClick={() => setAbierto((actual) => (actual === t.termino ? null : t.termino))}
              className={`min-h-9 rounded-full border px-3 text-xs font-semibold ${
                abierto === t.termino ? 'border-primary bg-primary-container text-on-primary-container' : 'border-outline-variant bg-surface-lowest text-primary'
              }`}
            >
              {t.termino}
            </button>
          ))}
        </div>
        {abierto && definicion && (
          <p className="flex items-start gap-2 rounded-xl bg-primary-container p-3 text-sm text-on-primary-container">
            <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              <strong>{abierto}:</strong> {definicion}
            </span>
          </p>
        )}
      </div>

      {voz.disponible && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={alternarVoz}
            className="flex min-h-10 items-center gap-2 rounded-full bg-surface-container px-4 text-sm font-semibold text-on-surface"
          >
            {voz.narrando ? <VolumeX size={16} aria-hidden="true" /> : <Volume2 size={16} aria-hidden="true" />}
            {voz.narrando ? 'Detener' : 'Escuchar'}
          </button>
          <button
            type="button"
            onClick={() => voz.narrar(textoNarrableDeJugada(jugada))}
            className="flex min-h-10 items-center gap-2 rounded-full bg-surface-container px-4 text-sm font-semibold text-on-surface"
          >
            <RotateCcw size={16} aria-hidden="true" />
            Explicámelo de nuevo
          </button>
        </div>
      )}
    </div>
  );
}

export default function Repaso({datos, clase, voz}: {datos: UltimaPartida; clase: string; voz: Narracion}) {
  const {cargandoHistorial, errorHistorial, ultima, analisis, analizando, errorAnalisis} = datos;
  const tarjetas = useMemo(() => tarjetasDeRepaso(analisis?.jugadas), [analisis]);

  if (cargandoHistorial) return <CargandoInline texto="Buscando tu última partida…" />;
  if (errorHistorial) return <ErrorReintentar mensaje={errorHistorial.message || 'No se pudo cargar tu historial de partidas.'} onReintentar={datos.reintentarHistorial} />;
  if (!ultima) return <Vacio>Todavía no jugaste ninguna partida. Juega tu primera partida y después Turing la repasa acá con vos.</Vacio>;
  if (analizando) return <CargandoInline texto="Turing está repasando tu partida…" />;
  if (errorAnalisis) return <ErrorReintentar mensaje={errorAnalisis.message || 'No se pudo analizar tu última partida.'} onReintentar={datos.reintentarAnalisis} />;

  const contraTuring = ultima.tipo_oponente === 'modelo';
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-surface-low p-3 text-xs text-on-surface-variant">
        <span className="flex items-center gap-2 font-semibold text-on-surface">
          {contraTuring ? <Brain size={14} aria-hidden="true" /> : <Bot size={14} aria-hidden="true" />}
          {contraTuring ? 'Turing IA' : 'Stockfish'} · Nivel {ultima.nivel} · {ultima.cantidad_jugadas} jugadas
        </span>
        <span>{fechaHoraLegible(ultima.fecha)}</span>
      </div>
      {tarjetas.length === 0 ? (
        <Vacio>En esa partida no hay jugadas tuyas para repasar.</Vacio>
      ) : (
        tarjetas.map((jugada) => (
          <TarjetaJugada key={jugada.numero_ply} jugada={jugada} tiempoMedioMs={analisis?.resumen.tiempo_medio_jugador_ms} clase={clase} voz={voz} />
        ))
      )}
    </>
  );
}
