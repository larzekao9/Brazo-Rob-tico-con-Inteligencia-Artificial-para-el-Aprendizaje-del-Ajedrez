import {useCallback, useEffect, useRef, useState} from 'react';
import {obtenerSala, unirseASala} from '../../api/sala';
import {esErrorDeConexion, mensajeDeError} from './salaUtil';
import type {ErrorApi, SalaEstado} from './tipos';

/** Cada cuántos ms se consulta la sala mientras la pestaña está visible (PLAN_MULTIJUGADOR.md §7.3). */
export const INTERVALO_POLLING_MS = 1500;

export interface ErrorSala {
  mensaje: string;
  /** true si fue de conexión (red caída o 5xx); false p. ej. para "No existe esa sala". */
  sinConexion: boolean;
}

function errorDeSala(err: unknown): ErrorSala {
  if ((err as ErrorApi | null)?.status === 404) return {mensaje: 'No existe esa sala.', sinConexion: false};
  return {mensaje: mensajeDeError(err, 'No se pudo cargar la sala.'), sinConexion: esErrorDeConexion(err)};
}

/**
 * Estado vivo de una sala. Al montar se une (POST /unirse, idempotente: devuelve el `rol` real o
 * "espectador") y recién ahí pinta; después consulta GET /sala/{codigo} cada 1,5 s solo con la
 * pestaña visible, se detiene al terminar y limpia timers y listeners al desmontar.
 * `version` descarta respuestas más viejas que lo que ya se muestra.
 */
export function useSala(codigo: string) {
  const [sala, setSala] = useState<SalaEstado | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<ErrorSala | null>(null);
  /** Aviso no bloqueante: el polling falló pero se conserva la última sala conocida. */
  const [reconectando, setReconectando] = useState(false);
  const [intento, setIntento] = useState(0);
  const salaRef = useRef<SalaEstado | null>(null);

  /** Acepta un estado nuevo solo si no es más viejo que el que ya se muestra. */
  const aplicarSala = useCallback((nueva: SalaEstado) => {
    const actual = salaRef.current;
    if (actual && actual.codigo === nueva.codigo && nueva.version < actual.version) return;
    salaRef.current = nueva;
    setSala(nueva);
  }, []);

  // Carga inicial: unirse (o enterarse de que se es espectador) y leer el estado.
  useEffect(() => {
    let activo = true;
    salaRef.current = null;
    setSala(null);
    setCargando(true);
    setError(null);
    (async () => {
      try {
        await unirseASala(codigo);
        const inicial = (await obtenerSala(codigo)) as SalaEstado;
        if (activo) aplicarSala(inicial);
      } catch (err) {
        if (activo) setError(errorDeSala(err));
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, [codigo, intento, aplicarSala]);

  const seguirViva = sala !== null && !sala.terminada;
  useEffect(() => {
    if (!seguirViva) return;
    let activo = true;
    let enVuelo = false;
    async function consultar() {
      if (enVuelo || document.visibilityState !== 'visible') return;
      enVuelo = true;
      try {
        const nueva = (await obtenerSala(codigo)) as SalaEstado;
        if (!activo) return;
        aplicarSala(nueva);
        setReconectando(false);
      } catch (err) {
        if (activo) setReconectando(esErrorDeConexion(err));
      } finally {
        enVuelo = false;
      }
    }
    const temporizador = window.setInterval(() => void consultar(), INTERVALO_POLLING_MS);
    // Al volver a la pestaña se consulta enseguida en vez de esperar al siguiente tic.
    const alCambiarVisibilidad = () => void consultar();
    document.addEventListener('visibilitychange', alCambiarVisibilidad);
    return () => {
      activo = false;
      window.clearInterval(temporizador);
      document.removeEventListener('visibilitychange', alCambiarVisibilidad);
    };
  }, [codigo, seguirViva, aplicarSala]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);

  return {sala, cargando, error, reconectando, reintentar, aplicarSala};
}
