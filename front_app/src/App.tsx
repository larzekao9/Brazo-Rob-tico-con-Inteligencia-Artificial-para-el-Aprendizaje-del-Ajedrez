import {useEffect, type ReactNode} from 'react';
import Cargando from './componentes/Cargando';
import ErrorReintentar from './componentes/ErrorReintentar';
import NavInferior from './componentes/NavInferior';
import {SesionProvider, useSesion} from './estado/SesionContext';
import {PAGINAS} from './paginas/registro';
import {RUTAS_PUBLICAS, consumirRutaPendiente, guardarRutaPendiente, reemplazarA, rutaActualCompleta, useRuta, type RutaApp} from './router';

/**
 * Rutas SIN barra de navegación inferior: la entrada (login, onboarding) y las pantallas inmersivas
 * donde la barra estorba o llevaría fuera de una partida en curso. Todas las demás la muestran.
 * - /jugar/partida/:id y /sala/:codigo: partida en curso (tablero a pantalla completa).
 * - /amigo y /sala/:codigo/analisis: parte del mismo flujo "jugar con un amigo"; se entra desde Inicio
 *   y cada pantalla trae su propio botón para volver (ninguna pestaña correspondería: no está en la barra).
 */
const SIN_NAVEGACION: readonly RutaApp[] = ['/login', '/onboarding', '/jugar/partida/:id', '/amigo', '/sala/:codigo', '/sala/:codigo/analisis'];

function Marco({children}: {children: ReactNode}) {
  return (
    <div className="flex min-h-dvh justify-center bg-surface-container">
      <div className="relative flex min-h-dvh w-full max-w-120 flex-col bg-surface shadow-xl shadow-on-surface/10">{children}</div>
    </div>
  );
}

function Contenido() {
  const {ruta} = useRuta();
  const {usuario, restaurando, errorRestauracion, reintentarRestauracion} = useSesion();
  const esPublica = RUTAS_PUBLICAS.includes(ruta);
  const sinServidor = errorRestauracion !== null;

  // Guardia de sesión: sin usuario solo se ve /login (guardando la ruta pedida para volver tras entrar,
  // p. ej. un enlace #/sala/K7M2QX); con usuario, /login manda a esa ruta guardada o al inicio.
  useEffect(() => {
    if (restaurando || sinServidor) return;
    if (!usuario && !esPublica) {
      guardarRutaPendiente(rutaActualCompleta());
      reemplazarA('/login');
    }
    if (usuario && ruta === '/login') reemplazarA(consumirRutaPendiente() ?? '/inicio');
  }, [restaurando, sinServidor, usuario, esPublica, ruta]);

  if (restaurando) return <Cargando mensaje="Restaurando sesión…" />;
  if (sinServidor) {
    // Los tokens se conservan: no se manda a /login por un fallo de red.
    return (
      <div className="flex flex-1 flex-col justify-center gap-3 p-4">
        <ErrorReintentar mensaje={errorRestauracion} onReintentar={reintentarRestauracion} />
      </div>
    );
  }
  if (!usuario && !esPublica) return null;

  const Pagina = PAGINAS[ruta];
  const conNavegacion = usuario !== null && !SIN_NAVEGACION.includes(ruta);
  return (
    <>
      <main className="flex-1">
        <Pagina />
      </main>
      {conNavegacion && <NavInferior />}
    </>
  );
}

export default function App() {
  return (
    <SesionProvider>
      <Marco>
        <Contenido />
      </Marco>
    </SesionProvider>
  );
}
