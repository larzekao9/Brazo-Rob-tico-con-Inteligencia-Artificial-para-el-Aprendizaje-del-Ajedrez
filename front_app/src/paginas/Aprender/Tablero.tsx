import {useState} from 'react';
import {ChevronLeft, CheckCircle, Grid, Palette, Compass} from 'lucide-react';
import {irA, useRuta} from '../../router';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import TableroDemo from '../../componentes/TableroDemo';

const DESTINOS_TABLERO = ['h1'];
const RESALTADAS_TABLERO = ['h1'];

const INFO_CARDS = [
  {icono: Grid, titulo: '64 cuadrados', subtitulo: '8 filas × 8 columnas', color: 'primary'},
  {icono: Palette, titulo: 'Colores', subtitulo: 'Claros y oscuros alternados', color: 'secondary'},
  {icono: Compass, titulo: 'Orientación', subtitulo: 'Cuadro blanco a la derecha', color: 'primary'},
];

export default function Tablero() {
  const {ruta} = useRuta();
  const [pasoActual, setPasoActual] = useState(0);

  const pasos = [
    {
      titulo: 'El Tablero',
      descripcion: 'El ajedrez se juega entre dos personas que mueven las piezas alternativamente. El juego se desarrolla sobre un tablero que contiene <strong>64 cuadrados</strong>, organizados en 8 filas y 8 columnas.',
      destinos: DESTINOS_TABLERO,
      resaltadas: RESALTADAS_TABLERO,
      etiqueta: 'h1: Blanca a la derecha',
    },
    {
      titulo: 'Colores del tablero',
      descripcion: 'Las casillas se alternan entre claras y oscuras. No importa el material del tablero: siempre hay 32 casillas claras y 32 oscuras.',
      destinos: [],
      resaltadas: ['a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1'],
      etiqueta: 'Fila 1: patrón claro-oscuro',
    },
    {
      titulo: 'Orientación correcta',
      descripcion: 'La regla de oro: <strong>cada jugador debe tener a su derecha un cuadro blanco</strong>. Para Blancas, la casilla h1 es clara; para Negras, la casilla a8 es clara.',
      destinos: [],
      resaltadas: ['h1', 'a8'],
      etiqueta: 'h1 (Blancas) / a8 (Negras) — siempre claras',
    },
  ];

  const paso = pasos[pasoActual];
  const progreso = (pasoActual + 1) / pasos.length;

  const handleSiguiente = () => {
    if (pasoActual < pasos.length - 1) {
      setPasoActual(pasoActual + 1);
    } else {
      irA('/aprender/piezas');
    }
  };

  const handleAnterior = () => {
    if (pasoActual > 0) {
      setPasoActual(pasoActual - 1);
    } else {
      irA('/aprender');
    }
  };

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur-md border-b border-outline-variant px-4 py-3">
        <div className="flex items-center justify-between">
          <button onClick={handleAnterior} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
          <div className="flex-1 text-center">
            <p className="text-xs font-medium text-primary tracking-wide">FUNDAMENTOS</p>
            <h1 className="font-titulo text-xl font-bold text-on-surface">El Tablero</h1>
          </div>
          <div className="w-10" />
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-outline-variant overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{width: `${progreso * 100}%`}}
          />
        </div>
        <p className="text-xs text-on-surface-variant text-center mt-1">{pasoActual + 1} de {pasos.length}</p>
      </header>

      <main className="flex-1 p-4 space-y-4 overflow-y-auto pb-24">
        <GlassCard>
          <div className="flex items-center justify-between mb-4">
            <span className="px-2 py-1 rounded-full bg-surface-container text-primary text-xs font-medium">
              Fundamentos
            </span>
            <span className="px-2 py-1 rounded-full bg-primary-container/30 text-primary text-xs font-medium flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-primary" />
              Modo interactivo
            </span>
          </div>

          <h2 className="font-titulo text-xl font-bold text-on-surface mb-2 text-center">{paso.titulo}</h2>
          <div className="prose prose-sm text-on-surface-variant max-w-none mx-auto mb-4" dangerouslySetInnerHTML={{__html: paso.descripcion}} />

          <div className="relative aspect-square max-w-sm mx-auto mb-4">
            <TableroDemo
              fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
              destinos={paso.destinos}
              resaltadas={paso.resaltadas}
              ariaLabel={`Tablero ilustrativo: ${paso.titulo}`}
            />
            {(paso.destinos.length > 0 || paso.resaltadas.length > 0) && (
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container/90 backdrop-blur-sm shadow-md">
                <CheckCircle size={14} className="text-secondary" />
                <span className="text-xs font-medium text-on-surface">{paso.etiqueta}</span>
              </div>
            )}
          </div>
        </GlassCard>

        <div className="grid gap-3">
          {INFO_CARDS.map((card, i) => (
            <GlassCard key={card.titulo} className="text-center">
              <div className={`w-12 h-12 rounded-xl bg-${card.color}-container/30 flex items-center justify-center mx-auto mb-3`}>
                <card.icono size={24} className={`text-${card.color}`} />
              </div>
              <h3 className="font-titulo font-semibold text-on-surface">{card.titulo}</h3>
              <p className="text-on-surface-variant text-sm mt-1">{card.subtitulo}</p>
            </GlassCard>
          ))}
        </div>

        <GlassCard className="bg-primary-container/10 border-primary/20">
          <div className="flex items-center gap-3">
            <CheckCircle size={24} className="text-primary" />
            <div>
              <p className="font-medium text-primary">Importante</p>
              <p className="text-on-surface-variant text-sm">
                El tablero debe estar orientado correctamente. Recuerda la regla de oro:
                <strong> cada jugador debe tener a su derecha un cuadro blanco</strong>.
              </p>
            </div>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="font-titulo text-lg font-semibold text-on-surface mb-3">Comprobación rápida</h3>
          <p className="text-on-surface-variant text-sm">
            Si eres Blancas, la casilla inferior derecha es <span className="font-bold text-primary">h1</span>.
            Si eres Negras, es <span className="font-bold text-primary">a8</span>. Ambas son siempre casillas claras.
          </p>
        </GlassCard>

        <div className="flex gap-3">
          <button onClick={handleAnterior} className="flex-1 px-4 py-3 rounded-lg bg-surface-container text-on-surface font-medium hover:bg-surface-container/80 transition-colors">
            Anterior
          </button>
          <BotonPrimario onClick={handleSiguiente} className="flex-1">
            {pasoActual === pasos.length - 1 ? 'Siguiente: Las Piezas' : 'Siguiente'}
            <ChevronLeft size={16} className="ml-2 rotate-180" />
          </BotonPrimario>
        </div>
      </main>
    </div>
  );
}