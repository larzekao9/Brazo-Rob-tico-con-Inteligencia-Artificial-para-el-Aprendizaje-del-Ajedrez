import {useCallback, useState} from 'react';
import {ChevronLeft, Eye, Flag} from 'lucide-react';
import {abandonarSala, jugadasLegalesSala, moverEnSala} from '../../api/sala';
import BotonPrimario from '../../componentes/BotonPrimario';
import Chip from '../../componentes/Chip';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import GlassCard from '../../componentes/GlassCard';
import HistorialJugadas from '../../componentes/HistorialJugadas';
import TableroAjedrez from '../../componentes/TableroAjedrez';
import {esPromocionDePeon} from '../../dominio/ajedrez';
import {fenTrasJugada} from '../../dominio/movimiento';
import type {Color} from '../../dominio/tablero';
import {irA} from '../../router';
import SelectorPromocion from '../Jugar/SelectorPromocion';
import {colorDeRol, mensajeDeError, turnoComoColor} from './salaUtil';
import TarjetaFin from './TarjetaFin';
import type {JugadorSala, SalaEstado} from './tipos';

interface Props {
  sala: SalaEstado;
  /** Aplica un estado más nuevo de la sala (lo usa la respuesta de mover/abandonar). */
  aplicarSala: (sala: SalaEstado) => void;
  /** El polling no llega al servidor; se sigue mostrando la última posición. */
  reconectando: boolean;
}

/** Jugada ya enviada que se muestra al instante hasta que el backend responde (o se revierte). */
interface Optimista {
  fenBase: string;
  fen: string;
  uci: string;
}

function FilaJugador({jugador, color, activo, etiqueta}: {jugador: JugadorSala | null; color: Color; activo: boolean; etiqueta: string}) {
  return (
    <div className={`flex items-center justify-between gap-2 rounded-boton px-3 py-2 ${activo ? 'bg-primary-container text-on-primary-container' : 'bg-surface-low text-on-surface'}`}>
      <span className="flex min-w-0 items-center gap-2">
        <span aria-hidden="true" className={`size-4 shrink-0 rounded-full border border-outline ${color === 'w' ? 'bg-surface-lowest' : 'bg-on-surface'}`} />
        <span className="truncate font-titulo text-sm font-bold">{jugador?.nombre ?? 'Esperando…'}</span>
        <span className="shrink-0 text-xs opacity-80">{etiqueta}</span>
      </span>
      {activo && <span className="shrink-0 text-xs font-semibold">Su turno</span>}
    </div>
  );
}

/** Tablero de una sala: jugar si eres blancas/negras, mirar si eres espectador. */
export default function SalaTablero({sala, aplicarSala, reconectando}: Props) {
  const esEspectador = sala.rol === 'espectador';
  const color = colorDeRol(sala.rol);
  const rival: Color = color === 'w' ? 'b' : 'w';
  const turno = turnoComoColor(sala.turno);
  const enJuego = !sala.terminada;
  const [optimista, setOptimista] = useState<Optimista | null>(null);
  const [promocion, setPromocion] = useState<{origen: string; destino: string} | null>(null);
  const [errorJugada, setErrorJugada] = useState<string | null>(null);
  const [confirmandoAbandono, setConfirmandoAbandono] = useState(false);
  const [abandonando, setAbandonando] = useState(false);

  // La jugada optimista solo vale mientras la sala siga en la posición desde la que se jugó.
  const mostrada = optimista && optimista.fenBase === sala.fen ? optimista : null;
  const fen = mostrada?.fen ?? sala.fen;
  const enviando = mostrada !== null;
  const jugador = (c: Color) => (c === 'w' ? sala.blancas : sala.negras);

  const obtenerDestinos = useCallback((casilla: string) => jugadasLegalesSala(sala.codigo, casilla) as Promise<string[]>, [sala.codigo]);

  async function mover(uci: string) {
    setErrorJugada(null);
    setOptimista({fenBase: sala.fen, fen: fenTrasJugada(sala.fen, uci), uci});
    try {
      aplicarSala((await moverEnSala(sala.codigo, uci)) as SalaEstado);
    } catch (err) {
      // Rollback: sin jugada optimista el tablero vuelve a la posición real.
      setErrorJugada(mensajeDeError(err, 'No se pudo aplicar la jugada.'));
    } finally {
      setOptimista(null);
    }
  }

  function intentarMover(origen: string, destino: string) {
    if (esPromocionDePeon(sala.fen, origen, destino)) setPromocion({origen, destino});
    else void mover(origen + destino);
  }

  function coronar(pieza: string) {
    if (!promocion) return;
    const {origen, destino} = promocion;
    setPromocion(null);
    void mover(origen + destino + pieza);
  }

  async function abandonar() {
    setAbandonando(true);
    setErrorJugada(null);
    try {
      aplicarSala((await abandonarSala(sala.codigo)) as SalaEstado);
    } catch (err) {
      setErrorJugada(mensajeDeError(err, 'No se pudo abandonar la partida.'));
    } finally {
      setAbandonando(false);
      setConfirmandoAbandono(false);
    }
  }

  const miTurno = !esEspectador && turno === color;
  const estado = esEspectador
    ? `Turno de las ${sala.turno}${jugador(turno) ? ` (${jugador(turno)?.nombre})` : ''}`
    : enviando
      ? 'Enviando tu jugada…'
      : miTurno
        ? 'Es tu turno'
        : `Turno de ${jugador(turno)?.nombre ?? 'tu rival'}`;

  return (
    <section className="flex flex-col gap-3 p-4 pb-8">
      <header className="flex items-center gap-2">
        <button type="button" onClick={() => irA('/inicio')} aria-label="Ir al inicio (la partida sigue)" className="flex size-11 shrink-0 items-center justify-center rounded-full text-on-surface hover:bg-surface-container">
          <ChevronLeft size={24} aria-hidden="true" />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-titulo text-lg font-bold text-on-surface">Sala {sala.codigo}</h1>
          <p className="text-xs text-on-surface-variant">{esEspectador ? 'Estás viendo esta partida' : `Juegas con las ${sala.rol}`}</p>
        </div>
        <Chip tono={enJuego ? 'primario' : 'neutro'}>{enJuego ? 'En juego' : 'Terminada'}</Chip>
      </header>

      {esEspectador && (
        <p role="status" className="flex items-center gap-2 rounded-boton bg-secondary-container px-4 py-3 text-sm font-semibold text-on-secondary-container">
          <Eye size={18} aria-hidden="true" /> Estás viendo esta partida. Solo lectura: no puedes mover.
        </p>
      )}
      {reconectando && (
        <p role="status" className="rounded-boton bg-tertiary-container px-4 py-2 text-sm font-medium text-on-tertiary-container">
          Reconectando con el servidor… se muestra la última posición conocida.
        </p>
      )}

      <FilaJugador jugador={jugador(rival)} color={rival} activo={enJuego && turno === rival} etiqueta={esEspectador ? `(${rival === 'w' ? 'blancas' : 'negras'})` : 'Rival'} />

      <TableroAjedrez
        fen={fen}
        orientacion={color}
        colorJugador={esEspectador ? null : color}
        ultimaJugada={mostrada?.uci ?? sala.ultima_jugada_uci}
        obtenerDestinos={obtenerDestinos}
        onMover={intentarMover}
        onError={setErrorJugada}
        deshabilitado={!enJuego || enviando || promocion !== null || abandonando}
      />

      <FilaJugador jugador={jugador(color)} color={color} activo={enJuego && turno === color} etiqueta={esEspectador ? `(${color === 'w' ? 'blancas' : 'negras'})` : 'Tú'} />

      <p role="status" aria-live="polite" className="text-center text-sm font-semibold text-on-surface-variant">
        {enJuego ? estado : 'Partida terminada'}
      </p>
      {errorJugada && <ErrorReintentar mensaje={errorJugada} />}

      {sala.terminada && <TarjetaFin sala={sala} />}

      <GlassCard className="max-h-56 overflow-y-auto">
        <h2 className="mb-2 font-titulo text-base font-bold text-on-surface">Jugadas</h2>
        <HistorialJugadas jugadas={sala.jugadas.map((san) => ({san}))} />
      </GlassCard>

      {enJuego &&
        !esEspectador &&
        (confirmandoAbandono ? (
          <GlassCard className="flex flex-col gap-2">
            <p className="text-sm text-on-surface">¿Abandonar? Ganará tu rival y la partida terminará.</p>
            <BotonPrimario variante="peligro" cargando={abandonando} textoCargando="Abandonando…" onClick={() => void abandonar()}>
              Sí, abandonar
            </BotonPrimario>
            <BotonPrimario variante="secundario" disabled={abandonando} onClick={() => setConfirmandoAbandono(false)}>
              Seguir jugando
            </BotonPrimario>
          </GlassCard>
        ) : (
          <BotonPrimario variante="secundario" onClick={() => setConfirmandoAbandono(true)}>
            <Flag size={18} aria-hidden="true" /> Abandonar
          </BotonPrimario>
        ))}

      {promocion && <SelectorPromocion color={color} onElegir={coronar} onCancelar={() => setPromocion(null)} />}
    </section>
  );
}
