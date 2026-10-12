import {createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode} from 'react';
import {login as loginApi, obtenerPerfil, registro as registroApi} from '../api/backend';
import {obtenerEstadisticasUsuario} from '../api/extra';
import {alPerderSesion, borrarTokens, guardarTokens, hayTokens} from '../api/sesionHttp';
import {reemplazarA} from '../router';

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
  /** Mensaje si al restaurar no se pudo hablar con el servidor (los tokens se conservan). */
  errorRestauracion: string | null;
  /** Vuelve a intentar restaurar la sesión tras un error de conexión. */
  reintentarRestauracion(): void;
  estadisticas: Estadisticas | null;
  login(email: string, password: string): Promise<void>;
  registrar(email: string, nombre: string, password: string): Promise<void>;
  /** Vuelve a leer el usuario (nivel, foto, etc.) desde /auth/me. */
  recargarUsuario(): Promise<void>;
  cargarEstadisticas(): Promise<void>;
  cerrarSesion(): void;
}

const ROL_JUGADOR = 'jugador';

const Contexto = createContext<ValorSesion | null>(null);

export function SesionProvider({children}: {children: ReactNode}) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [estadisticas, setEstadisticas] = useState<Estadisticas | null>(null);
  const [restaurando, setRestaurando] = useState<boolean>(() => hayTokens());
  const [errorRestauracion, setErrorRestauracion] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const cerrarSesion = useCallback(() => {
    borrarTokens();
    // Primero la ruta pública: así el guardia no guarda esta pantalla como "ruta pendiente".
    reemplazarA('/login');
    setUsuario(null);
    setEstadisticas(null);
  }, []);

  // Un 401 a mitad de sesión que no se pudo renovar: sesionHttp ya borró los tokens y el guardia
  // de App.tsx lleva a /login guardando la ruta actual.
  useEffect(
    () =>
      alPerderSesion(() => {
        setUsuario(null);
        setEstadisticas(null);
      }),
    [],
  );

  const recargarUsuario = useCallback(async () => {
    setUsuario((await obtenerPerfil()) as Usuario);
  }, []);

  const cargarEstadisticas = useCallback(async () => {
    setEstadisticas((await obtenerEstadisticasUsuario()) as Estadisticas);
  }, []);

  // Restaurar sesión: GET /auth/me (con un refresh si da 401, ver sesionHttp). Los errores de conexión
  // NO borran los tokens: se ofrece reintentar. Un rechazo definitivo ya borró los tokens.
  useEffect(() => {
    if (!hayTokens()) {
      setRestaurando(false);
      return;
    }
    let activo = true;
    setRestaurando(true);
    setErrorRestauracion(null);
    obtenerPerfil()
      .then((perfil: Usuario) => {
        if (!activo) return;
        if (perfil.rol === ROL_JUGADOR) setUsuario(perfil);
        else borrarTokens();
      })
      .catch((err: unknown) => {
        if (!activo) return;
        const sinConexion = err instanceof Error && (err as Error & {sinConexion?: boolean}).sinConexion;
        if (sinConexion) setErrorRestauracion(err.message);
        // Otro error (p. ej. 401 sin refresh válido): los tokens ya se descartaron y se va a /login.
      })
      .finally(() => {
        if (activo) setRestaurando(false);
      });
    return () => {
      activo = false;
    };
  }, [intento]);

  const reintentarRestauracion = useCallback(() => setIntento((n) => n + 1), []);

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
    () => ({
      usuario,
      restaurando,
      errorRestauracion,
      reintentarRestauracion,
      estadisticas,
      login,
      registrar,
      recargarUsuario,
      cargarEstadisticas,
      cerrarSesion,
    }),
    [usuario, restaurando, errorRestauracion, reintentarRestauracion, estadisticas, login, registrar, recargarUsuario, cargarEstadisticas, cerrarSesion],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(Contexto);
  if (!valor) throw new Error('useSesion debe usarse dentro de <SesionProvider>');
  return valor;
}
