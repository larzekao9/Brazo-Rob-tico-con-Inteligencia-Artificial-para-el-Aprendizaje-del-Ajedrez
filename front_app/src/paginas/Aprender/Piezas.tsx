import {useState} from 'react';
import {ChevronLeft, CheckCircle, HelpCircle} from 'lucide-react';
import {irA, useRuta} from '../../router';
import {PIEZAS} from '../../dominio/contenido/piezas';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import TableroDemo from '../../componentes/TableroDemo';
import Cargando from '../../componentes/Cargando';

const DESTINOS_POR_PIEZA: Record<string, string[]> = {
  rey: ['e2', 'f2', 'd2', 'e1', 'f1', 'd1'],
  dama: ['d2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'a5', 'b5', 'c5', 'e5', 'f5', 'g5', 'h5', 'a1', 'b1', 'c1', 'e1', 'f1', 'g1', 'h1'],
  torre: ['a1', 'b1', 'c1', 'd1', 'f1', 'g1', 'h1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8'],
  alfil: ['c1', 'e1', 'b2', 'd2', 'f2', 'a3', 'g3', 'h4'],
  caballo: ['f3', 'd3', 'c4', 'c2', 'b3', 'b1'],
  peon: ['e3', 'e4', 'd3', 'd4', 'f3', 'f4'],
};

const MOVIMIENTOS_DEMO: Record<string, {origen: string; destinos: string[]}> = {
  rey: {origen: 'e1', destinos: ['e2', 'f2', 'd2', 'f1', 'd1']},
  dama: {origen: 'd1', destinos: ['d2', 'd3', 'd4', 'd5', 'a4', 'b5', 'c6', 'e2', 'f3', 'g4', 'h5']},
  torre: {origen: 'a1', destinos: ['a2', 'a3', 'a4', 'a5', 'b1', 'c1', 'd1', 'e1', 'f1']},
  alfil: {origen: 'c1', destinos: ['d2', 'e3', 'f4', 'g5', 'h6', 'b2', 'a3']},
  caballo: {origen: 'g1', destinos: ['f3', 'h3', 'e2']},
  peon: {origen: 'e2', destinos: ['e3', 'e4', 'd3', 'f3']},
};

export default function Piezas() {
  const {ruta} = useRuta();
  const [piezaSeleccionada, setPiezaSeleccionada] = useState<string | null>(null);
  const [pasoActual, setPasoActual] = useState(0);

  const piezaActual = PIEZAS[pasoActual];
  const demo = MOVIMIENTOS_DEMO[piezaActual.tipo];
  const destinos = demo ? demo.destinos : [];

  const handleSiguiente = () => {
    if (pasoActual < PIEZAS.length - 1) {
      setPasoActual(pasoActual + 1);
      setPiezaSeleccionada(null);
    } else {
      irA('/aprender/tablero');
    }
  };

  const handleAnterior = () => {
    if (pasoActual > 0) {
      setPasoActual(pasoActual - 1);
      setPiezaSeleccionada(null);
    } else {
      irA('/aprender');
    }
  };

  const progreso = (pasoActual + 1) / PIEZAS.length;

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur-md border-b border-outline-variant px-4 py-3">
        <div className="flex items-center justify-between">
          <button onClick={handleAnterior} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
          <div className="flex-1 text-center">
            <p className="text-xs font-medium text-primary tracking-wide">FUNDAMENTOS</p>
            <h1 className="font-titulo text-xl font-bold text-on-surface">Las Piezas</h1>
          </div>
          <div className="w-10" />
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-outline-variant overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{width: `${progreso * 100}%`}}
          />
        </div>
        <p className="text-xs text-on-surface-variant text-center mt-1">{pasoActual + 1} de {PIEZAS.length}</p>
      </header>

      <main className="flex-1 p-4 space-y-4 overflow-y-auto pb-24">
        <GlassCard>
          <div className="flex items-center justify-between mb-4">
            <span className="px-2 py-1 rounded-full bg-surface-container text-primary text-xs font-medium">
              Fundamentos
            </span>
            <span className="px-2 py-1 rounded-full bg-secondary-container/30 text-secondary text-xs font-medium flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-secondary" />
              Modo interactivo
            </span>
          </div>

          <h2 className="font-titulo text-xl font-bold text-on-surface mb-2 text-center">
            ¿Cuántas piezas tiene cada jugador?
          </h2>
          <p className="text-on-surface-variant text-center mb-4">
            Las piezas de ajedrez se dividen en claras y oscuras (<strong>Blancas</strong> y <strong>Negras</strong>).
            Cada bando comanda exactamente 16 combatientes organizados en rangos tácticos.
          </p>

          <div className="relative aspect-square max-w-sm mx-auto mb-4">
            <TableroDemo
              fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
              destinos={destinos}
              resaltadas={demo ? [demo.origen] : []}
              ariaLabel={`Tablero demostrando movimientos del ${piezaActual.nombre}`}
            />
            {demo && (
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container/90 backdrop-blur-sm shadow-md">
                <CheckCircle size={14} className="text-secondary" />
                <span className="text-xs font-medium text-on-surface">
                  Casilla {demo.origen.toUpperCase()}: {piezaActual.nombre} {'Blancas' /* demo piece */}
                </span>
              </div>
            )}
          </div>

          <div className="text-center">
            <span className="px-3 py-1 rounded-full bg-surface-container text-on-surface-variant text-xs font-medium">
              {piezaActual.nombre} → {destinos.length} casillas destino
            </span>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="font-titulo text-lg font-semibold text-on-surface mb-4 text-center">{piezaActual.nombre}</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-surface-container">
              <span className="text-3xl">{piezaActual.apodo}</span>
              <div>
                <p className="font-medium text-on-surface">{piezaActual.nombre}</p>
                <p className="text-xs text-on-surface-variant">{piezaActual.articulo} {piezaActual.apodo.toLowerCase()}</p>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-primary-container/20 border border-primary/20">
              <p className="font-medium text-primary mb-1">¿Cómo se mueve?</p>
              <p className="text-on-surface text-sm">{piezaActual.comoSeMueve}</p>
            </div>
            <div className="p-3 rounded-xl bg-secondary-container/20 border border-secondary/20">
              <p className="font-medium text-secondary mb-1">Regla especial</p>
              <p className="text-on-surface text-sm">{piezaActual.reglaEspecial}</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="bg-primary-container/10 border-primary/20">
          <div className="flex items-center gap-3">
            <HelpCircle size={24} className="text-primary" />
            <div>
              <p className="font-medium text-primary">IMPORTANTE</p>
              <p className="text-on-surface-variant text-sm">
                Cada jugador comienza con <strong>16 piezas</strong>. En total hay <strong>32 piezas</strong> sobre el tablero al inicio de la partida.
              </p>
            </div>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="font-titulo text-lg font-semibold text-on-surface mb-3">Comprobación rápida</h3>
          <p className="text-on-surface-variant text-sm">
            1 Rey + 1 Dama + 2 Torres + 2 Alfiles + 2 Caballos + 8 Peones ={' '}
            <span className="font-bold text-primary">16 piezas</span>
          </p>
        </GlassCard>

        <div className="flex gap-3">
          <button onClick={handleAnterior} className="flex-1 px-4 py-3 rounded-lg bg-surface-container text-on-surface font-medium hover:bg-surface-container/80 transition-colors">
            Anterior
          </button>
          <BotonPrimario onClick={handleSiguiente} className="flex-1">
            {pasoActual === PIEZAS.length - 1 ? 'Siguiente: El Tablero' : 'Siguiente'}
            <ChevronLeft size={16} className="ml-2 rotate-180" />
          </BotonPrimario>
        </div>
      </main>
    </div>
  );
}