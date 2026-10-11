import {useEffect, useMemo, useRef, useState} from 'react';
import {analisisCompletoPartida, historialPartidasPropio} from '../../../api/backend';

export interface PartidaResumen {
  id: string;
  fecha: string;
  resultado: string;
  tipo_oponente: string;
  nivel: number;
  cantidad_jugadas: number;
}

export interface JugadaAnalisis {
  numero_ply: number;
  quien?: string;
  jugada_san: string;
  mejor_jugada_motor?: string;
  calidad: string;
  principio_ajedrecistico?: string;
  explicacion: string;
  tiempo_ms?: number | null;
}

export interface ResumenAnalisis {
  precision_global: number;
  precision_jugador?: number | null;
  consejo_tutor?: string;
  duracion_ms?: number | null;
  tiempo_medio_jugador_ms?: number | null;
}

export interface Analisis {
  jugadas: JugadaAnalisis[];
  resumen: ResumenAnalisis;
}

export interface UltimaPartida {
  cargandoHistorial: boolean;
  errorHistorial: Error | null;
  /** Total de partidas del jugador (0 si todavía no jugó ninguna). */
  totalPartidas: number;
  /** La última partida con al menos una jugada, o null. */
  ultima: PartidaResumen | null;
  analisis: Analisis | null;
  /** true mientras se espera el análisis (incluye el instante entre abrir la sección y que arranque el pedido). */
  analizando: boolean;
  errorAnalisis: Error | null;
  reintentarAnalisis(): void;
  reintentarHistorial(): void;
}

/**
 * Última partida del jugador y su análisis completo. El historial se pide al entrar; el análisis
 * (lo más pesado: lo calcula Stockfish) solo cuando `necesitaAnalisis` es true, y una sola vez por
 * partida y rango aunque se cierre y se vuelva a abrir la sección.
 */
export function useUltimaPartida(rango: string, necesitaAnalisis: boolean): UltimaPartida {
  const [intentoHistorial, setIntentoHistorial] = useState(0);
  const [historial, setHistorial] = useState<{total: number; partidas: PartidaResumen[]} | null>(null);
  const [cargandoHistorial, setCargandoHistorial] = useState(true);
  const [errorHistorial, setErrorHistorial] = useState<Error | null>(null);

  const [analisis, setAnalisis] = useState<Analisis | null>(null);
  const [cargandoAnalisis, setCargandoAnalisis] = useState(false);
  const [errorAnalisis, setErrorAnalisis] = useState<Error | null>(null);
  const [intentoAnalisis, setIntentoAnalisis] = useState(0);
  const pedidoRef = useRef<string | null>(null);

  useEffect(() => {
    let vigente = true;
    setCargandoHistorial(true);
    setErrorHistorial(null);
    historialPartidasPropio(5, 0)
      .then((datos: {total: number; partidas: PartidaResumen[]}) => vigente && setHistorial(datos))
      .catch((err: Error) => vigente && setErrorHistorial(err))
      .finally(() => vigente && setCargandoHistorial(false));
    return () => {
      vigente = false;
    };
  }, [intentoHistorial]);

  // Una partida recién creada y nunca jugada no sirve para repasar.
  const ultima = useMemo(() => (historial?.partidas ?? []).find((p) => p.cantidad_jugadas > 0) ?? null, [historial]);
  const ultimaId = ultima?.id ?? null;

  useEffect(() => {
    if (!ultimaId || !necesitaAnalisis) return;
    const clave = `${ultimaId}|${rango}|${intentoAnalisis}`;
    if (pedidoRef.current === clave) return;
    pedidoRef.current = clave;
    setCargandoAnalisis(true);
    setErrorAnalisis(null);
    analisisCompletoPartida(ultimaId, rango)
      .then((datos: Analisis) => {
        if (pedidoRef.current === clave) setAnalisis(datos);
      })
      .catch((err: Error) => {
        if (pedidoRef.current === clave) setErrorAnalisis(err);
      })
      .finally(() => {
        if (pedidoRef.current === clave) setCargandoAnalisis(false);
      });
  }, [ultimaId, rango, necesitaAnalisis, intentoAnalisis]);

  const analizando = cargandoAnalisis || (necesitaAnalisis && ultimaId !== null && !analisis && !errorAnalisis);

  return {
    cargandoHistorial,
    errorHistorial,
    totalPartidas: historial?.total ?? 0,
    ultima,
    analisis,
    analizando,
    errorAnalisis,
    reintentarAnalisis: () => setIntentoAnalisis((n) => n + 1),
    reintentarHistorial: () => setIntentoHistorial((n) => n + 1),
  };
}
