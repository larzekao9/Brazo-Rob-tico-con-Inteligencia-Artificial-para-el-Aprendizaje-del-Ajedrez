import {useSyncExternalStore} from 'react';

/** Rutas fijas de la app (PLAN_FRONT_APP.md §4). Los segmentos `:x` son parámetros. */
export const RUTAS = [
  '/login',
  '/onboarding',
  '/inicio',
  '/jugar',
  '/jugar/config',
  '/jugar/partida/:id',
  '/jugar/resultado/:id',
  '/aprender',
  '/aprender/piezas',
  '/aprender/tablero',
  '/aprender/filas-columnas',
  '/aprender/posicion-inicial',
  '/aprender/tutor',
  '/historial',
  '/perfil',
  '/demostracion',
  '/amigo',
  '/sala/:codigo',
  '/sala/:codigo/analisis',
] as const;

export type RutaApp = (typeof RUTAS)[number];
export type ParamsRuta = Record<string, string>;

export const RUTA_POR_DEFECTO: RutaApp = '/inicio';
/** Rutas que se pueden ver sin sesión. */
export const RUTAS_PUBLICAS: readonly RutaApp[] = ['/login'];

/** Reemplaza `:param` por su valor: construirRuta('/jugar/partida/:id', {id: 'x'}) -> '/jugar/partida/x'. */
export function construirRuta(ruta: string, params: ParamsRuta = {}): string {
  return ruta.replace(/:(\w+)/g, (_, nombre: string) => encodeURIComponent(params[nombre] ?? ''));
}

/** Busca qué patrón de RUTAS calza con un path real y extrae sus parámetros. */
export function resolverRuta(path: string): {ruta: RutaApp; params: ParamsRuta} {
  const limpio = path.split('?')[0].replace(/\/+$/, '') || '/';
  const segmentos = limpio.split('/');
  for (const patron of RUTAS) {
    const partes = patron.split('/');
    if (partes.length !== segmentos.length) continue;
    const params: ParamsRuta = {};
    const calza = partes.every((parte, i) => {
      if (parte.startsWith(':')) {
        params[parte.slice(1)] = decodeURIComponent(segmentos[i]);
        return segmentos[i] !== '';
      }
      return parte === segmentos[i];
    });
    if (calza) return {ruta: patron, params};
  }
  return {ruta: RUTA_POR_DEFECTO, params: {}};
}

function pathActual(): string {
  return window.location.hash.replace(/^#/, '') || RUTA_POR_DEFECTO;
}

function suscribir(avisar: () => void): () => void {
  window.addEventListener('hashchange', avisar);
  return () => window.removeEventListener('hashchange', avisar);
}

/** Navega a una ruta fija, con parámetros si el patrón los tiene. */
export function irA(ruta: string, params?: ParamsRuta): void {
  window.location.hash = construirRuta(ruta, params);
}

/** Como `irA` pero sin dejar la ruta actual en el historial (útil para redirecciones). */
export function reemplazarA(ruta: string, params?: ParamsRuta): void {
  const destino = `#${construirRuta(ruta, params)}`;
  window.history.replaceState(null, '', destino);
  window.dispatchEvent(new HashChangeEvent('hashchange'));
}

/** Ruta actual (el patrón, p. ej. '/jugar/partida/:id') y sus parámetros. */
export function useRuta(): {ruta: RutaApp; params: ParamsRuta} {
  const path = useSyncExternalStore(suscribir, pathActual, () => RUTA_POR_DEFECTO);
  return resolverRuta(path);
}

const CLAVE_RUTA_PENDIENTE = 'ruta_pendiente';

/** Ruta actual del hash (p. ej. '/sala/K7M2QX'), con parámetros ya resueltos. */
export function rutaActualCompleta(): string {
  return pathActual();
}

/**
 * Enlace profundo con login: guarda la ruta pedida (sessionStorage, con try/catch) para volver a ella
 * después de iniciar sesión o registrarse. No guarda /login ni la ruta por defecto.
 */
export function guardarRutaPendiente(path: string): void {
  if (!path.startsWith('/') || path === '/login' || path === RUTA_POR_DEFECTO) return;
  try {
    sessionStorage.setItem(CLAVE_RUTA_PENDIENTE, path);
  } catch {
    /* sin almacenamiento: se vuelve al inicio */
  }
}

/** Devuelve y olvida la ruta guardada con `guardarRutaPendiente` (o null). */
export function consumirRutaPendiente(): string | null {
  try {
    const path = sessionStorage.getItem(CLAVE_RUTA_PENDIENTE);
    sessionStorage.removeItem(CLAVE_RUTA_PENDIENTE);
    return path;
  } catch {
    return null;
  }
}
