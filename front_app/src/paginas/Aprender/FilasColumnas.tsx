import {useState} from 'react';
import {ChevronLeft, CheckCircle, Pin, MoveHorizontal, MoveVertical, MapPin} from 'lucide-react';
import {irA, useRuta} from '../../router';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import TableroDemo from '../../componentes/TableroDemo';

const DESTINOS_COLUMNA_E = ['e8', 'e7', 'e6', 'e5', 'e4', 'e3', 'e2', 'e1'];
const DESTINOS_FILA_4 = ['a4', 'b4', 'c4', 'd4', 'e4', 'f4', 'g4', 'h4'];
const RESALTADA_INTERSECCION = ['e4'];

const INFO_CARDS = [
  {icono: MoveHorizontal, titulo: '8 Filas (Horizontales)', subtitulo: 'Se identifican con números del 1 al 8, de abajo hacia arriba.', color: 'primary'},
  {icono: MoveVertical, titulo: '8 Columnas (Verticales)', subtitulo: 'Se identifican con letras de la \'a\' a la \'h\', de izquierda a derecha.', color: 'secondary'},
  {icono: MapPin, titulo: 'Coordenadas (Casillas)', subtitulo: 'Cada casilla tiene un nombre único: letra + número (ej. e4, c6).', color: 'primary'},
];

export default function FilasColumnas() {
  const {ruta} = useRuta();
  const [pasoActual, setPasoActual] = useState(0);

  const pasos = [
    {
      titulo: 'Filas y Columnas',
      descripcion: 'Para nombrar cada casilla y mover las piezas, el tablero se divide en líneas horizontales llamadas <strong>filas</strong> (numeradas del 1 al 8) y líneas verticales llamadas <strong>columnas</strong> (identificadas con letras de la \'a\' a la \'h\').',
      destinos: [...DESTINOS_COLUMNA_E, ...DESTINOS_FILA_4],
      resaltadas: RESALTADA_INTERSECCION,
      etiqueta: 'Columna e (vertical) + Fila 4 (horizontal) = e4',
    },
    {
      titulo: 'La columna e',
      descripcion: 'La columna <strong>e</strong> es la columna central del rey. Las piezas que la controlan tienen gran influencia en la partida.',
      destinos: DESTINOS_COLUMNA_E,
      resaltadas: DESTINOS_COLUMNA_E,
      etiqueta: 'Columna e completa',
    },
    {
      titulo: 'La fila 4',
      descripcion: 'La fila <strong>4</strong> es una fila central. Junto con la fila 5, forma el centro del tablero donde se libran las batallas principales.',
      destinos: DESTINOS_FILA_4,
      resaltadas: DESTINOS_FILA_4,
      etiqueta: 'Fila 4 completa',
    },
  ];

  const paso = pasos[pasoActual];
  const progreso = (pasoActual + 1) / pasos.length;

  const handleSiguiente = () => {
    if (pasoActual < pasos.length - 1) {
      setPasoActual(pasoActual + 1);
    } else {
      irA('/aprender/posicion-inicial');
    }
  };

  const handleAnterior = () => {
    if (pasoActual > 0) {
      setPasoActual(pasoActual - 1);
    } else {
      irA('/aprender/piezas');
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
            <p className="text-xs font-medium text-primary tracking-wide">APRENDIENDO AJEDREZ</p>
            <h1 className="font-titulo text-xl font-bold text-on-surface">Filas y Columnas</h1>
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
            <span className="px-2 py-1 rounded-full bg-surface-container text-secondary text-xs font-medium">
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
                <Pin size={14} className="text-primary" />
                <span className="text-xs font-medium text-on-surface">{paso.etiqueta}</span>
              </div>
            )}
          </div>
        </GlassCard>

        <div className="grid gap-3">
          {INFO_CARDS.map((card) => (
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
            <Pin size={24} className="text-primary" />
            <div>
              <p className="font-medium text-primary">Regla de Nombrado</p>
              <p className="text-on-surface-variant text-sm">
                Primero siempre se menciona la <strong>letra de la columna</strong> y después el <strong>número de la fila</strong>.
                Por eso decimos casilla <strong>e4</strong>, nunca 4e.
              </p>
            </div>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="font-titulo text-lg font-semibold text-on-surface mb-3">Comprobación rápida</h3>
          <p className="text-on-surface-variant text-sm">
            En la notación ajedrecística universal, las letras siempre se escriben en minúsculas:
            <span className="font-bold text-primary">a1</span>, <span className="font-bold text-primary">d4</span>, <span className="font-bold text-primary">h8</span>.
          </p>
        </GlassCard>

        <div className="flex gap-3">
          <button onClick={handleAnterior} className="flex-1 px-4 py-3 rounded-lg bg-surface-container text-on-surface font-medium hover:bg-surface-container/80 transition-colors">
            Anterior
          </button>
          <BotonPrimario onClick={handleSiguiente} className="flex-1">
            {pasoActual === pasos.length - 1 ? 'Siguiente: Posición Inicial' : 'Siguiente'}
            <ChevronLeft size={16} className="ml-2 rotate-180" />
          </BotonPrimario>
        </div>
      </main>
    </div>
  );
}