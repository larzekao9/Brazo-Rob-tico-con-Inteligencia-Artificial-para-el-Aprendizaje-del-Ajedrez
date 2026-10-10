import {useEffect, type ReactNode} from 'react';
import Cargando from './componentes/Cargando';
import NavInferior from './componentes/NavInferior';
import {SesionProvider, useSesion} from './estado/SesionContext';
import {PAGINAS} from './paginas/registro';
import {RUTAS_PUBLICAS, reemplazarA, useRuta} from './router';

/** Rutas donde no se muestra la navegación inferior (flujo de entrada y partida en curso). */
const SIN_NAVEGACION = ['/login', '/onboarding', '/jugar/partida/:id'];

function Marco({children}: {children: ReactNode}) {
  return (
    <div className="flex min-h-dvh justify-center bg-surface-container">
      <div className="relative flex min-h-dvh w-full max-w-120 flex-col bg-surface shadow-xl shadow-on-surface/10">{children}</div>
    </div>
  );
}

function Contenido() {
  const {ruta} = useRuta();
  const {usuario, restaurando} = useSesion();
  const esPublica = RUTAS_PUBLICAS.includes(ruta);

  // Guardia de sesión: sin usuario solo se ve /login; con usuario, /login manda al inicio.
  useEffect(() => {
    if (restaurando) return;
    if (!usuario && !esPublica) reemplazarA('/login');
    if (usuario && ruta === '/login') reemplazarA('/inicio');
  }, [restaurando, usuario, esPublica, ruta]);

  if (restaurando) return <Cargando mensaje="Restaurando sesión…" />;
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
