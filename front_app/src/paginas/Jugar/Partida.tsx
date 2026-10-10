import {useEffect, useState} from 'react';
import {LogOut} from 'lucide-react';
import BarraEvaluacion from '../../componentes/BarraEvaluacion';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import Chip from '../../componentes/Chip';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import GlassCard from '../../componentes/GlassCard';
import HistorialJugadas from '../../componentes/HistorialJugadas';
import RelojAjedrez from '../../componentes/RelojAjedrez';
import TableroAjedrez from '../../componentes/TableroAjedrez';
import {esPromocionDePeon, turnoDeFen} from '../../dominio/ajedrez';
import type {Color} from '../../dominio/tablero';
import {irA, reemplazarA, useRuta} from '../../router';
import {colorDelJugador, veredictoDe} from './partidaUtil';
import SelectorPromocion from './SelectorPromocion';
import {OPONENTES, type TipoOponente} from './seleccion';
import {usePartida} from './usePartida';
import {useRelojes} from './useRelojes';

const TEXTO_VEREDICTO = {victoria: '¡Ganaste!', derrota: 'Perdiste esta partida', tablas: 'Tablas'} as const;

export default function Partida() {
  const {params} = useRuta();
  const id = params.id ?? '';
  const {partida, cargando, errorCarga, errorJugada, setErrorJugada, enviando, evaluacion, probabilidadVictoria, ultimaJugada, cargar, mover, obtenerDestinos} =
    usePartida(id);
  const [promocion, setPromocion] = useState<{origen: string; destino: string} | null>(null);
  const [confirmandoSalida, setConfirmandoSalida] = useState(false);

  const color: Color = partida ? colorDelJugador(partida.fen_inicial) : 'w';
  const turno = partida ? (turnoDeFen(partida.fen) as Color) : 'w';
  const enJuego = partida !== null && !partida.terminada;
  // Mientras la jugada viaja al backend y responde la IA, el tiempo corre para el rival.
  const turnoDelReloj: Color = enviando ? (color === 'w' ? 'b' : 'w') : turno;
  const relojes = useRelojes(turnoDelReloj, enJuego, id);

  // Una partida que ya estaba terminada al abrirla no tiene nada que jugar: va directo al resultado.
  // (Si termina mientras se juega, se queda en el tablero final con el botón "Ver resultado".)
  useEffect(() => {
    if (!cargando && partida?.terminada) reemplazarA('/jugar/resultado/:id', {id: partida.id});
    // Solo al terminar de cargar: los cambios posteriores de `partida` vienen de jugar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargando]);

  if (cargando) return <Cargando mensaje="Cargando partida…" />;
  if (errorCarga || !partida) {
    return (
      <section className="flex flex-col gap-3 p-4">
        <ErrorReintentar mensaje={errorCarga ?? 'No se encontró la partida.'} onReintentar={() => void cargar()} />
        <BotonPrimario variante="secundario" onClick={() => irA('/jugar')}>
          Volver a Jugar
        </BotonPrimario>
      </section>
    );
  }

  const oponente = OPONENTES[partida.tipo_oponente as TipoOponente]?.titulo ?? partida.tipo_oponente;
  const veredicto = veredictoDe(partida.resultado, color);
  const turnoDelJugador = turno === color;

  function intentarMover(origen: string, destino: string) {
    if (!partida) return;
    if (esPromocionDePeon(partida.fen, origen, destino)) setPromocion({origen, destino});
    else void mover(origen + destino);
  }

  function coronar(codigo: string) {
    if (!promocion) return;
    const {origen, destino} = promocion;
    setPromocion(null);
    void mover(origen + destino + codigo);
  }

  const estado = enviando ? 'Tu jugada se envió. La IA está pensando…' : turnoDelJugador ? 'Es tu turno' : 'Turno del rival';
  const jugadas = partida.jugadas.map((san) => ({san}));

  return (
    <section className="flex flex-col gap-3 p-4 pb-8">
      <header className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <h1 className="truncate font-titulo text-lg font-bold text-on-surface">{oponente}</h1>
          <p className="text-xs text-on-surface-variant">Nivel {partida.nivel} · Juegas con {color === 'w' ? 'blancas' : 'negras'}</p>
        </div>
        <Chip tono={enJuego ? 'primario' : 'neutro'}>{enJuego ? 'En juego' : 'Terminada'}</Chip>
      </header>

      <RelojAjedrez etiqueta="Rival" segundos={relojes[color === 'w' ? 'b' : 'w']} activo={enJuego && !turnoDelJugador} umbralPocoTiempo={-1} />
      <BarraEvaluacion evaluacionCp={evaluacion?.cp ?? null} mateEn={evaluacion?.mate ?? null} />

      <TableroAjedrez
        fen={partida.fen}
        orientacion={color}
        colorJugador={color}
        ultimaJugada={ultimaJugada}
        obtenerDestinos={obtenerDestinos}
        onMover={intentarMover}
        onError={setErrorJugada}
        deshabilitado={!enJuego || enviando || promocion !== null}
      />

      <RelojAjedrez etiqueta="Tú" segundos={relojes[color]} activo={enJuego && turnoDelJugador} umbralPocoTiempo={-1} />

      <p role="status" aria-live="polite" className="text-center text-sm font-semibold text-on-surface-variant">
        {enJuego ? estado : 'Partida terminada'}
      </p>
      {errorJugada && <ErrorReintentar mensaje={errorJugada} />}
      {probabilidadVictoria !== null && enJuego && (
        <p className="text-center text-xs text-on-surface-variant">Probabilidad de ganar estimada: {Math.round(probabilidadVictoria)}%</p>
      )}

      {partida.terminada && (
        <GlassCard className="flex flex-col gap-3 border-primary bg-primary-container">
          <h2 className="font-titulo text-xl font-bold text-on-primary-container">{veredicto ? TEXTO_VEREDICTO[veredicto] : 'Partida terminada'}</h2>
          <p className="text-sm text-on-primary-container">Resultado: {partida.resultado}</p>
          <BotonPrimario onClick={() => reemplazarA('/jugar/resultado/:id', {id: partida.id})}>Ver resultado y análisis</BotonPrimario>
        </GlassCard>
      )}

      <GlassCard className="max-h-56 overflow-y-auto">
        <h2 className="mb-2 font-titulo text-base font-bold text-on-surface">Jugadas</h2>
        <HistorialJugadas jugadas={jugadas} />
      </GlassCard>

      {enJuego &&
        (confirmandoSalida ? (
          <GlassCard className="flex flex-col gap-2">
            <p className="text-sm text-on-surface">La partida queda guardada: puedes retomarla desde Jugar.</p>
            <BotonPrimario variante="peligro" onClick={() => irA('/inicio')}>
              Salir de la partida
            </BotonPrimario>
            <BotonPrimario variante="secundario" onClick={() => setConfirmandoSalida(false)}>
              Seguir jugando
            </BotonPrimario>
          </GlassCard>
        ) : (
          <BotonPrimario variante="secundario" onClick={() => setConfirmandoSalida(true)}>
            <LogOut size={18} aria-hidden="true" /> Salir de la partida
          </BotonPrimario>
        ))}

      {promocion && <SelectorPromocion color={color} onElegir={coronar} onCancelar={() => setPromocion(null)} />}
    </section>
  );
}
