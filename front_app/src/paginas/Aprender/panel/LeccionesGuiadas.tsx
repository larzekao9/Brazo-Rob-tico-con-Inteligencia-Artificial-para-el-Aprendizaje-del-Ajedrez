import {ChevronRight} from 'lucide-react';
import {irA} from '../../../router';

const LECCIONES = [
  {ruta: '/aprender/tablero', titulo: 'El tablero', detalle: 'Casillas, colores y orientación'},
  {ruta: '/aprender/piezas', titulo: 'Las piezas', detalle: 'Cómo se mueve cada una'},
  {ruta: '/aprender/filas-columnas', titulo: 'Filas y columnas', detalle: 'Cómo se nombran las casillas'},
  {ruta: '/aprender/posicion-inicial', titulo: 'Posición inicial', detalle: 'Dónde empieza cada pieza'},
  {ruta: '/aprender/tutor', titulo: 'Tutor Turing', detalle: 'Chat para resolver tus dudas'},
] as const;

/** Enlaces a las lecciones paso a paso (pantallas propias). */
export default function LeccionesGuiadas() {
  return (
    <ul className="flex flex-col gap-2">
      {LECCIONES.map((l, i) => (
        <li key={l.ruta}>
          <button
            type="button"
            onClick={() => irA(l.ruta)}
            className="flex min-h-14 w-full items-center gap-3 rounded-2xl border border-outline-variant bg-surface-lowest px-4 text-left"
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-container text-sm font-bold text-primary" aria-hidden="true">
              {i + 1}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-on-surface">{l.titulo}</span>
              <span className="block text-xs text-on-surface-variant">{l.detalle}</span>
            </span>
            <ChevronRight size={18} className="shrink-0 text-on-surface-variant" aria-hidden="true" />
          </button>
        </li>
      ))}
    </ul>
  );
}
