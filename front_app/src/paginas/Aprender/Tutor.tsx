import {ChevronLeft} from 'lucide-react';
import {useSesion} from '../../estado/SesionContext';
import {irA} from '../../router';
import ChatTuring from './panel/ChatTuring';
import {useNarracion} from './panel/voz';

/** Chat con el tutor Turing en pantalla completa (el mismo componente que usa el panel de Aprender). */
export default function Tutor() {
  const {usuario} = useSesion();
  const voz = useNarracion();

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="sticky top-0 z-10 border-b border-outline-variant bg-surface/80 px-4 py-3 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => irA('/aprender')} className="flex size-10 items-center justify-center rounded-full hover:bg-surface-container" aria-label="Volver a Aprender">
            <ChevronLeft size={24} aria-hidden="true" />
          </button>
          <div>
            <p className="text-xs font-medium tracking-wide text-primary">APRENDER</p>
            <h1 className="font-titulo text-xl font-bold text-on-surface">Tutor Turing</h1>
          </div>
        </div>
      </header>
      <div className="flex flex-1 flex-col p-4">
        <ChatTuring usuario={usuario} voz={voz} lleno />
      </div>
    </div>
  );
}
