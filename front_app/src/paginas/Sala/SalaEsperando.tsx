import {useRef, useState} from 'react';
import {Check, ChevronLeft, Copy, Share2} from 'lucide-react';
import BotonPrimario from '../../componentes/BotonPrimario';
import GlassCard from '../../componentes/GlassCard';
import {irA} from '../../router';
import BotonCancelarSala from './BotonCancelarSala';
import {enlaceDeSala} from './enlace';
import type {SalaEstado} from './tipos';

/** Sala creada que aún no tiene rival: código grande, enlace para compartir y cancelar. */
export default function SalaEsperando({sala}: {sala: SalaEstado}) {
  const enlace = enlaceDeSala(sala.codigo);
  const campo = useRef<HTMLInputElement>(null);
  const [copiado, setCopiado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const esCreador = sala.rol !== 'espectador';

  /** Copia el enlace; si el portapapeles no está disponible deja el campo seleccionado para copiarlo a mano. */
  async function copiar() {
    setAviso(null);
    try {
      await navigator.clipboard.writeText(enlace);
      setCopiado(true);
      window.setTimeout(() => setCopiado(false), 2000);
    } catch {
      campo.current?.focus();
      campo.current?.select();
      setAviso('No se pudo copiar automáticamente: el enlace quedó seleccionado, cópialo con tu teclado.');
    }
  }

  async function compartir() {
    if (!navigator.share) return copiar();
    try {
      await navigator.share({title: 'Juega ajedrez conmigo', text: `Únete a mi sala ${sala.codigo}`, url: enlace});
    } catch (err) {
      // Cerrar el panel de compartir no es un error; cualquier otro fallo cae en copiar.
      if (!(err instanceof DOMException && err.name === 'AbortError')) await copiar();
    }
  }

  return (
    <section className="flex flex-col gap-4 p-4">
      <header className="flex items-center gap-2">
        <button type="button" onClick={() => irA('/inicio')} aria-label="Volver al inicio" className="flex size-11 items-center justify-center rounded-full text-on-surface hover:bg-surface-container">
          <ChevronLeft size={24} aria-hidden="true" />
        </button>
        <h1 className="font-titulo text-xl font-bold text-on-surface">Esperando a tu rival</h1>
      </header>

      <GlassCard className="flex flex-col items-center gap-3 text-center">
        <p className="text-sm text-on-surface-variant">Código de la sala</p>
        <p aria-label={`Código ${sala.codigo.split('').join(' ')}`} className="select-all font-titulo text-5xl font-bold tracking-widest text-primary">
          {sala.codigo}
        </p>
        {esCreador && <p className="text-sm text-on-surface-variant">Juegas con las {sala.rol}.</p>}
        <p role="status" aria-live="polite" className="flex items-center gap-2 text-sm font-semibold text-on-surface-variant">
          <span className="size-4 animate-spin rounded-full border-2 border-surface-highest border-t-primary" aria-hidden="true" />
          La partida empieza sola cuando se una.
        </p>
      </GlassCard>

      <GlassCard className="flex flex-col gap-3">
        <label htmlFor="enlace-sala" className="text-sm font-semibold text-on-surface-variant">
          Enlace para compartir
        </label>
        <input
          id="enlace-sala"
          ref={campo}
          readOnly
          value={enlace}
          onFocus={(e) => e.currentTarget.select()}
          className="w-full rounded-boton border border-outline-variant bg-surface-lowest px-3 py-3 text-sm text-on-surface"
        />
        {aviso && (
          <p role="alert" className="text-sm text-error">
            {aviso}
          </p>
        )}
        <div className="flex gap-2">
          <BotonPrimario variante="secundario" onClick={() => void copiar()}>
            {copiado ? <Check size={18} aria-hidden="true" /> : <Copy size={18} aria-hidden="true" />}
            {copiado ? 'Copiado' : 'Copiar'}
          </BotonPrimario>
          <BotonPrimario onClick={() => void compartir()}>
            <Share2 size={18} aria-hidden="true" /> Compartir
          </BotonPrimario>
        </div>
      </GlassCard>

      {esCreador ? (
        <BotonCancelarSala codigo={sala.codigo} alCancelar={() => irA('/inicio')} />
      ) : (
        <BotonPrimario variante="secundario" onClick={() => irA('/inicio')}>
          Volver al inicio
        </BotonPrimario>
      )}
    </section>
  );
}
