import {Lock, Search, Trophy, UserPlus} from 'lucide-react';

const FUNCIONES = [
  {titulo: 'Invitar a un amigo', Icono: UserPlus},
  {titulo: 'Buscar rival de mi nivel', Icono: Search},
  {titulo: 'Ranking', Icono: Trophy},
];

/** Visión de tesis (multijugador y ranking): deshabilitadas a propósito, se dice claro que no existen todavía. */
export default function Proximamente() {
  return (
    <>
      <p className="text-sm text-on-surface-variant">Estas funciones todavía no están disponibles.</p>
      <ul className="flex flex-col gap-2">
        {FUNCIONES.map(({titulo, Icono}) => (
          <li key={titulo}>
            <button type="button" disabled aria-label={`${titulo} (próximamente)`} className="flex min-h-12 w-full items-center gap-3 rounded-2xl border border-outline-variant bg-surface-low px-4 text-sm font-semibold text-on-surface-variant opacity-70">
              <Icono size={18} aria-hidden="true" />
              <span className="flex-1 text-left">{titulo}</span>
              <Lock size={14} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
