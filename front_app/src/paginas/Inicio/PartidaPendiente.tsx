import {useEffect, useState} from 'react';
import {Flag, Play} from 'lucide-react';
import {obtenerPartidaEnCurso} from '../../api/backend';
import {abandonarPartida} from '../../api/extra';
import BotonPrimario from '../../componentes/BotonPrimario';
import GlassCard from '../../componentes/GlassCard';
import {irA} from '../../router';
import {OPONENTES, type TipoOponente} from '../Jugar/seleccion';

interface PartidaEnCurso {
  id: string;
  tipo_oponente: string;
  nivel: number;
  jugadas?: string[];
}

/** Tarjeta de Inicio: si hay una partida sin terminar, permite reanudarla o darla por terminada. */
export default function PartidaPendiente({alTerminar}: {alTerminar: () => void}) {
  const [partida, setPartida] = useState<PartidaEnCurso | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [terminando, setTerminando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    // Es opcional: si la consulta falla simplemente no se muestra la tarjeta.
    obtenerPartidaEnCurso()
      .then((p: PartidaEnCurso | null) => {
        if (activo) setPartida(p);
      })
      .catch(() => {
        if (activo) setPartida(null);
      });
    return () => {
      activo = false;
    };
  }, []);

  if (!partida) return null;

  const oponente = OPONENTES[partida.tipo_oponente as TipoOponente]?.titulo ?? partida.tipo_oponente;
  const jugadas = partida.jugadas?.length ?? 0;

  async function terminar() {
    if (!partida) return;
    setTerminando(true);
    setError(null);
    try {
      await abandonarPartida(partida.id);
      setPartida(null);
      alTerminar();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo terminar la partida.');
      setConfirmando(false);
    } finally {
      setTerminando(false);
    }
  }

  return (
    <GlassCard className="flex flex-col gap-3 border-secondary/40">
      <div>
        <h2 className="font-titulo text-lg font-bold text-on-surface">Tienes una partida sin terminar</h2>
        <p className="text-sm text-on-surface-variant">
          Contra {oponente}, nivel {partida.nivel} · {jugadas} {jugadas === 1 ? 'jugada' : 'jugadas'}.
        </p>
      </div>
      {error && (
        <p role="alert" className="text-sm text-error">
          {error}
        </p>
      )}
      {confirmando ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-on-surface">¿Terminarla? Contará como derrota.</p>
          <div className="flex gap-2">
            <BotonPrimario variante="peligro" cargando={terminando} onClick={() => void terminar()}>
              Sí, terminar
            </BotonPrimario>
            <BotonPrimario variante="secundario" disabled={terminando} onClick={() => setConfirmando(false)}>
              Cancelar
            </BotonPrimario>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <BotonPrimario onClick={() => irA('/jugar/partida/:id', {id: partida.id})}>
            <Play size={18} aria-hidden="true" /> Reanudar
          </BotonPrimario>
          <BotonPrimario variante="secundario" onClick={() => setConfirmando(true)}>
            <Flag size={18} aria-hidden="true" /> Terminar
          </BotonPrimario>
        </div>
      )}
    </GlassCard>
  );
}
