import {createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode} from 'react';
import {login as loginApi, obtenerPerfil, registro as registroApi} from '../api/backend';
import {obtenerEstadisticasUsuario} from '../api/extra';

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  rol: string;
  avatar_url: string | null;
  nivel_estimado: number | null;
  rango_estimado: string | null;
  edad: number | null;
  descripcion: string | null;
  diagnostico_completado: boolean;
  partidas_calibradas: number;
}

export interface Estadisticas {
  total_partidas: number;
  partidas_ganadas: number;
  partidas_perdidas: number;
  partidas_tablas: number;
  win_percent_promedio: number;
  racha_victoria_actual: number;
  precision_promedio: number;
  top_errores: {tipo: string; cantidad: number}[];
}

interface ValorSesion {
  usuario: Usuario | null;
  /** true mientras se valida el token guardado con /auth/me al abrir la app. */
  restaurando: boolean;
  estadisticas: Estadisticas | null;
  login(email: string, password: string): Promise<void>;
  registrar(email: string, nombre: string, password: string): Promise<void>;
  /** Vuelve a leer el usuario (nivel, foto, etc.) desde /auth/me. */
  recargarUsuario(): Promise<void>;
  cargarEstadisticas(): Promise<void>;
  cerrarSesion(): void;
}

const CLAVE_TOKEN = 'access_token';
const CLAVE_REFRESCO = 'refresh_token';
const ROL_JUGADOR = 'jugador';

function leerToken(): string | null {
  try {
    return localStorage.getItem(CLAVE_TOKEN);
  } catch {
    return null;
  }
}

function guardarTokens(acceso: string, refresco?: string): void {
  try {
    localStorage.setItem(CLAVE_TOKEN, acceso);
    if (refresco) localStorage.setItem(CLAVE_REFRESCO, refresco);
  } catch {
    /* sin almacenamiento: la sesión dura solo mientras la pestaña esté abierta */
  }
}

function borrarTokens(): void {
  try {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_REFRESCO);
  } catch {
    /* nada que borrar */
  }
}

const Contexto = createContext<ValorSesion | null>(null);

export function SesionProvider({children}: {children: ReactNode}) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [estadisticas, setEstadisticas] = useState<Estadisticas | null>(null);
  const [restaurando, setRestaurando] = useState<boolean>(() => leerToken() !== null);

  const cerrarSesion = useCallback(() => {
    borrarTokens();
    setUsuario(null);
    setEstadisticas(null);
  }, []);

  const recargarUsuario = useCallback(async () => {
    setUsuario((await obtenerPerfil()) as Usuario);
  }, []);

  const cargarEstadisticas = useCallback(async () => {
    setEstadisticas((await obtenerEstadisticasUsuario()) as Estadisticas);
  }, []);

  // Restaurar sesión: si hay token se valida con /auth/me; si falla, se descarta.
  useEffect(() => {
    if (leerToken() === null) return;
    let activo = true;
    obtenerPerfil()
      .then((perfil: Usuario) => {
        if (!activo) return;
        if (perfil.rol === ROL_JUGADOR) setUsuario(perfil);
        else borrarTokens();
      })
      .catch(() => borrarTokens())
      .finally(() => {
        if (activo) setRestaurando(false);
      });
    return () => {
      activo = false;
    };
  }, []);

  const aceptarRespuestaAuth = useCallback((datos: {tokens: {access_token: string; refresh_token?: string}; usuario: Usuario}) => {
    if (datos.usuario.rol !== ROL_JUGADOR) throw new Error('Esta app es solo para jugadores.');
    guardarTokens(datos.tokens.access_token, datos.tokens.refresh_token);
    setUsuario(datos.usuario);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      aceptarRespuestaAuth(await loginApi(email.trim(), password, ROL_JUGADOR));
    },
    [aceptarRespuestaAuth],
  );

  const registrar = useCallback(
    async (email: string, nombre: string, password: string) => {
      const correo = email.trim();
      aceptarRespuestaAuth(await registroApi(correo, nombre.trim() || correo.split('@')[0], password, ROL_JUGADOR, null));
    },
    [aceptarRespuestaAuth],
  );

  const valor = useMemo<ValorSesion>(
    () => ({usuario, restaurando, estadisticas, login, registrar, recargarUsuario, cargarEstadisticas, cerrarSesion}),
    [usuario, restaurando, estadisticas, login, registrar, recargarUsuario, cargarEstadisticas, cerrarSesion],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(Contexto);
  if (!valor) throw new Error('useSesion debe usarse dentro de <SesionProvider>');
  return valor;
}
