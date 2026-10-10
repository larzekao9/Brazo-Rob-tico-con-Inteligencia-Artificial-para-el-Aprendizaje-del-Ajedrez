import {useState} from 'react';
import {ArrowLeft, Info} from 'lucide-react';
import {crearPartida} from '../../api/backend';
import BotonPrimario from '../../componentes/BotonPrimario';
import Chip from '../../componentes/Chip';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import GlassCard from '../../componentes/GlassCard';
import {useSesion} from '../../estado/SesionContext';
import {irA} from '../../router';
import {NIVEL_DIAGNOSTICO, OPONENTES, etiquetaDeNivel, nivelMaximo, oponenteDeLaUrl, type TipoOponente} from './seleccion';

const NIVEL_POR_DEFECTO = 5;

export default function Configuracion() {
  const {usuario} = useSesion();
  const diagnosticoPendiente = usuario?.diagnostico_completado !== true;
  // Igual que la web: la primera partida es de diagnóstico, siempre contra Stockfish nivel fijo.
  const oponente: TipoOponente = diagnosticoPendiente ? 'motor' : oponenteDeLaUrl();
  const maximo = nivelMaximo(oponente);
  const nivelPerfil = usuario?.nivel_estimado ?? NIVEL_POR_DEFECTO;
  const [nivelElegido, setNivelElegido] = useState(nivelPerfil);
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nivel = diagnosticoPendiente ? NIVEL_DIAGNOSTICO : Math.min(nivelElegido, maximo);

  async function comenzar() {
    setCreando(true);
    setError(null);
    try {
      const partida = await crearPartida(nivel, null, oponente);
      irA('/jugar/partida/:id', {id: partida.id});
    } catch (err) {
      const rechazada = (err as Error & {status?: number}).status === 400;
      const mensaje = err instanceof Error ? err.message : 'No se pudo crear la partida.';
      setError(rechazada ? `El servidor rechazó la configuración (${mensaje}). Prueba con otro nivel u oponente.` : mensaje);
      setCreando(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 p-4">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => irA('/jugar')}
          aria-label="Volver a elegir oponente"
          className="flex size-11 items-center justify-center rounded-full bg-surface-low text-on-surface"
        >
          <ArrowLeft size={22} aria-hidden="true" />
        </button>
        <div>
          <h1 className="font-titulo text-2xl font-bold text-on-surface">Configurar partida</h1>
          <p className="text-sm text-on-surface-variant">Revisa el oponente y el nivel.</p>
        </div>
      </header>

      {diagnosticoPendiente && (
        <GlassCard className="flex gap-3 bg-secondary-container text-on-secondary-container">
          <Info size={22} className="shrink-0" aria-hidden="true" />
          <p className="text-sm font-medium">
            Tu primera partida mide tu nivel: se juega contra Stockfish en nivel {NIVEL_DIAGNOSTICO}. Después podrás elegir libremente.
          </p>
        </GlassCard>
      )}

      <GlassCard className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold text-on-surface-variant">Oponente</h2>
        <p className="font-titulo text-lg font-bold text-on-surface">{OPONENTES[oponente].titulo}</p>
        <p className="text-sm text-on-surface-variant">{OPONENTES[oponente].descripcion}</p>
        {oponente === 'modelo' && (
          <p className="text-xs text-on-surface-variant">El modelo decide sus jugadas por su cuenta, sin consultar a Stockfish.</p>
        )}
      </GlassCard>

      <GlassCard className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <label htmlFor="nivel" className="font-titulo text-base font-bold text-on-surface">
            Nivel de dificultad
          </label>
          <Chip tono="primario">
            Nivel {nivel}
            {etiquetaDeNivel(nivel) ? ` · ${etiquetaDeNivel(nivel)}` : ''}
          </Chip>
        </div>
        <input
          id="nivel"
          type="range"
          min={0}
          max={maximo}
          step={1}
          value={nivel}
          disabled={diagnosticoPendiente}
          onChange={(e) => setNivelElegido(Number(e.target.value))}
          aria-valuetext={`Nivel ${nivel}`}
          className="w-full accent-primary disabled:opacity-50"
        />
        <div className="flex justify-between text-xs text-on-surface-variant">
          <span>Fácil</span>
          <span>Difícil</span>
        </div>
        {!diagnosticoPendiente && usuario?.nivel_estimado != null && (
          <p className="text-xs text-on-surface-variant">Empieza en tu nivel medido ({usuario.nivel_estimado}); puedes cambiarlo.</p>
        )}
      </GlassCard>

      <GlassCard className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-on-surface-variant">Tu color</h2>
        <Chip tono="neutro">Blancas (empiezas tú)</Chip>
      </GlassCard>

      {error && <ErrorReintentar mensaje={error} />}
      <BotonPrimario cargando={creando} textoCargando="Creando partida…" onClick={() => void comenzar()}>
        Comenzar partida
      </BotonPrimario>
    </section>
  );
}
