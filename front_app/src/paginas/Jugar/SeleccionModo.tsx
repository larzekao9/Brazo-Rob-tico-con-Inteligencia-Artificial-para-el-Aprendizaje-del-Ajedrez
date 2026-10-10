import {useEffect, useState} from 'react';
import {BrainCircuit, ChevronRight, Cpu, PlayCircle} from 'lucide-react';
import {obtenerPartidaEnCurso} from '../../api/backend';
import BotonPrimario from '../../componentes/BotonPrimario';
import Chip from '../../componentes/Chip';
import GlassCard from '../../componentes/GlassCard';
import {irA} from '../../router';
import {OPONENTES, irAConfiguracion, type TipoOponente} from './seleccion';

interface PartidaEnCurso {
  id: string;
  tipo_oponente: string;
  nivel: number;
  jugadas?: string[];
}

const ICONOS: Record<TipoOponente, typeof Cpu> = {modelo: BrainCircuit, motor: Cpu};
const ORDEN: TipoOponente[] = ['modelo', 'motor'];

export default function SeleccionModo() {
  const [enCurso, setEnCurso] = useState<PartidaEnCurso | null>(null);
  const [avisoRetomar, setAvisoRetomar] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    obtenerPartidaEnCurso()
      .then((partida: PartidaEnCurso | null) => {
        if (activo) setEnCurso(partida);
      })
      .catch((err: Error) => {
        // 404/405: el backend desplegado no tiene el endpoint; se sigue sin la opción de retomar.
        if (activo && (err as Error & {status?: number}).status !== 404 && (err as Error & {status?: number}).status !== 405) {
          setAvisoRetomar('No pudimos comprobar si tienes una partida pendiente.');
        }
      });
    return () => {
      activo = false;
    };
  }, []);

  return (
    <section className="flex flex-col gap-4 p-4">
      <header>
        <h1 className="font-titulo text-2xl font-bold text-on-surface">¿Contra quién quieres jugar?</h1>
        <p className="text-sm text-on-surface-variant">Elige el oponente de tu próxima partida.</p>
      </header>

      {enCurso && (
        <GlassCard className="flex flex-col gap-3 border-primary bg-primary-container">
          <div className="flex items-center gap-2 text-on-primary-container">
            <PlayCircle size={22} aria-hidden="true" />
            <h2 className="font-titulo text-base font-bold">Tienes una partida en curso</h2>
          </div>
          <p className="text-sm text-on-primary-container">
            Contra {OPONENTES[enCurso.tipo_oponente as TipoOponente]?.titulo ?? enCurso.tipo_oponente}, nivel {enCurso.nivel}
            {typeof enCurso.jugadas?.length === 'number' ? ` · ${enCurso.jugadas.length} jugadas` : ''}.
          </p>
          <BotonPrimario onClick={() => irA('/jugar/partida/:id', {id: enCurso.id})}>Retomar partida</BotonPrimario>
        </GlassCard>
      )}
      {avisoRetomar && (
        <p role="status" className="text-sm text-on-surface-variant">
          {avisoRetomar}
        </p>
      )}

      <ul className="flex flex-col gap-3">
        {ORDEN.map((tipo) => {
          const {titulo, descripcion, insignia} = OPONENTES[tipo];
          const Icono = ICONOS[tipo];
          return (
            <li key={tipo}>
              <button
                type="button"
                onClick={() => irAConfiguracion(tipo)}
                className="flex w-full items-center gap-4 rounded-tarjeta border border-glass-border bg-glass p-4 text-left shadow-lg shadow-on-surface/5 transition-colors hover:bg-primary-container"
              >
                <span className="flex size-14 shrink-0 items-center justify-center rounded-boton bg-primary-container text-primary">
                  <Icono size={30} aria-hidden="true" />
                </span>
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="font-titulo text-lg font-bold text-on-surface">{titulo}</span>
                  <span className="text-sm text-on-surface-variant">{descripcion}</span>
                  <span>
                    <Chip tono={tipo === 'modelo' ? 'cian' : 'neutro'}>{insignia}</Chip>
                  </span>
                </span>
                <ChevronRight size={22} className="shrink-0 text-outline" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
