import {BookOpen, Home, Swords, User} from 'lucide-react';
import {irA, useRuta} from '../router';

const PESTANAS = [
  {ruta: '/inicio', etiqueta: 'Inicio', Icono: Home},
  {ruta: '/jugar', etiqueta: 'Jugar', Icono: Swords},
  {ruta: '/aprender', etiqueta: 'Aprender', Icono: BookOpen},
  {ruta: '/perfil', etiqueta: 'Perfil', Icono: User},
] as const;

/** Pestaña activa: la ruta actual cuelga de la pestaña (p. ej. /jugar/partida/:id -> Jugar). */
function esActiva(rutaActual: string, rutaPestana: string): boolean {
  return rutaActual === rutaPestana || rutaActual.startsWith(`${rutaPestana}/`);
}

export default function NavInferior() {
  const {ruta} = useRuta();
  return (
    <nav aria-label="Navegación principal" className="sticky bottom-0 z-20 border-t border-glass-border bg-glass-highlight backdrop-blur-md">
      <ul className="flex items-stretch justify-around px-2 pb-[env(safe-area-inset-bottom)]">
        {PESTANAS.map(({ruta: destino, etiqueta, Icono}) => {
          const activa = esActiva(ruta, destino);
          return (
            <li key={destino} className="flex-1">
              <button
                type="button"
                onClick={() => irA(destino)}
                aria-current={activa ? 'page' : undefined}
                className={`flex min-h-14 w-full flex-col items-center justify-center gap-0.5 rounded-boton text-xs font-semibold transition-colors ${
                  activa ? 'text-primary' : 'text-outline hover:text-on-surface'
                }`}
              >
                <span className={`flex h-7 w-14 items-center justify-center rounded-full ${activa ? 'bg-primary-container' : ''}`}>
                  <Icono size={20} aria-hidden="true" />
                </span>
                {etiqueta}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
