import {useState} from 'react';
import {ChevronLeft, CheckCircle, Flag, Award, GitCompareArrows} from 'lucide-react';
import {irA, useRuta} from '../../router';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import TableroDemo from '../../componentes/TableroDemo';

const FEN_INICIAL = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const DESTINOS_DAMA_BLANCA = ['d2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8'];
const DESTINOS_DAMA_NEGRA = ['d7', 'd6', 'd5', 'd4', 'd3', 'd2', 'd1'];
const RESALTADAS_DAMAS = ['d1', 'd8'];

const REGlas_ORO = [
  {
    icono: Award,
    titulo: 'La Dama y el Rey',
    mensaje: 'La Dama siempre va en la casilla de su <strong>propio color</strong>: la dama blanca en casilla clara (<strong>d1</strong>) y la dama negra en casilla oscura (<strong>d8</strong>). El Rey se sitúa justo a su lado en la columna <strong>e</strong>.',
    color: 'secondary',
  },
  {
    icono: GitCompareArrows,
    titulo: 'Enfrentados simétricamente',
    mensaje: 'Los Reyes y las Damas rivales se miran de frente a lo largo de las columnas centrales <strong>d</strong> y <strong>e</strong>, garantizando perfecta simetría en el despliegue.',
    color: 'primary',
  },
  {
    icono: Flag,
    titulo: 'Las blancas comienzan',
    mensaje: 'El jugador con piezas blancas siempre realiza el primer movimiento de la partida por convención y reglamento oficial internacional.',
    color: 'tertiary',
  },
];

export default function PosicionInicial() {
  const {ruta} = useRuta();
  const [pasoActual, setPasoActual] = useState(0);

  const pasos = [
    {
      titulo: 'La Posición Inicial',
      descripcion: 'El tablero se mira desde el lado de las blancas. Cada bando comienza con <strong>16 piezas</strong> preparadas simétricamente para la partida.',
      destinos: [...DESTINOS_DAMA_BLANCA, ...DESTINOS_DAMA_NEGRA],
      resaltadas: RESALTADAS_DAMAS,
      etiqueta: 'd1 = Dama Blanca (casilla clara) • d8 = Dama Negra (casilla oscura)',
    },
    {
      titulo: 'Despliegue completo',
      descripcion: 'Filas 1-2: Blancas (peones en fila 2, piezas en fila 1). Filas 7-8: Negras (peones en fila 7, piezas en fila 8). Total: 32 piezas.',
      destinos: [],
      resaltadas: ['a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1', 'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8'],
      etiqueta: 'Piezas mayores en filas 1 y 8',
    },
  ];

  const paso = pasos[pasoActual];
  const progreso = (pasoActual + 1) / pasos.length;

  const handleSiguiente = () => {
    if (pasoActual < pasos.length - 1) {
      setPasoActual(pasoActual + 1);
    } else {
      irA('/aprender/tutor');
    }
  };

  const handleAnterior = () => {
    if (pasoActual > 0) {
      setPasoActual(pasoActual - 1);
    } else {
      irA('/aprender/filas-columnas');
    }
  };

  const renderTableroCompleto = () => {
    const filas = [
      ['♜', '♞', '♝', '♛', '♚', '♝', '♞', '♜'],
      ['♟', '♟', '♟', '♟', '♟', '♟', '♟', '♟'],
      [null, null, null, null, null, null, null, null],
      [null, null, null, null, null, null, null, null],
      [null, null, null, null, null, null, null, null],
      [null, null, null, null, null, null, null, null],
      ['♙', '♙', '♙', '♙', '♙', '♙', '♙', '♙'],
      ['♖', '♘', '♗', '♕', '♔', '♗', '♘', '♖'],
    ];

    return (
      <div className="overflow-x-auto">
        <table className="w-full border-collapse mx-auto" style={{maxWidth: '100%'}}>
          <thead>
            <tr>
              <th className="w-8 text-center text-xs text-outline" />
              {['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'].map((col) => (
                <th key={col} className="w-10 text-center text-xs font-bold text-outline py-1">{col}</th>
              ))}
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {filas.map((fila, rowIndex) => {
              const rankNumber = 8 - rowIndex;
              return (
                <tr key={rankNumber}>
                  <td className="w-8 text-right pr-1 text-xs font-bold text-outline/50">{rankNumber}</td>
                  {fila.map((pieza, colIndex) => {
                    const esClara = (rowIndex + colIndex) % 2 === 0;
                    const esDamaBlanca = rowIndex === 7 && colIndex === 3;
                    const esDamaNegra = rowIndex === 0 && colIndex === 3;
                    return (
                      <td
                        key={`${rankNumber}-${colIndex}`}
                        className={`w-10 h-10 text-center relative ${esClara ? 'bg-board-light' : 'bg-board-dark'}`}
                        style={{fontSize: '22px'}}
                      >
                        {pieza && (
                          <span
                            className={`relative ${
                              esDamaBlanca || esDamaNegra
                                ? 'text-primary'
                                : pieza === pieza.toUpperCase()
                                ? 'text-emerald-700'
                                : 'text-slate-900'
                            }`}
                          >
                            {pieza}
                            {(esDamaBlanca || esDamaNegra) && (
                              <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-primary" />
                            )}
                          </span>
                        )}
                      </td>
                    );
                  })}
                  <td className="w-8 text-left pl-1 text-xs font-bold text-outline/50">{rankNumber}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
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
            <h1 className="font-titulo text-xl font-bold text-on-surface">La Posición Inicial</h1>
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
            <span className="px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium flex items-center gap-1">
              <CheckCircle size={10} />
              FUNDAMENTOS
            </span>
            <span className="px-2 py-1 rounded-full bg-primary-container/30 text-primary text-xs font-medium flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-primary" />
              Posición completa
            </span>
          </div>

          <h2 className="font-titulo text-xl font-bold text-on-surface mb-2 text-center">{paso.titulo}</h2>
          <div className="prose prose-sm text-on-surface-variant max-w-none mx-auto mb-4" dangerouslySetInnerHTML={{__html: paso.descripcion}} />

          {pasoActual === 0 ? (
            <div className="relative aspect-square max-w-sm mx-auto mb-4">
              <TableroDemo
                fen={FEN_INICIAL}
                destinos={paso.destinos}
                resaltadas={paso.resaltadas}
                ariaLabel="Posición inicial del ajedrez"
              />
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container/90 backdrop-blur-sm shadow-md">
                <CheckCircle size={14} className="text-primary" />
                <span className="text-xs font-medium text-on-surface">{paso.etiqueta}</span>
              </div>
            </div>
          ) : (
            <div className="mb-4">{renderTableroCompleto()}</div>
          )}

          {pasoActual === 0 && (
            <div className="flex items-center justify-center gap-4 text-xs text-on-surface-variant mb-2">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full border-2 border-primary" />
                Negras (Filas 7-8)
              </span>
              <span className="px-2 py-1 rounded-full bg-surface-container font-bold">32 Piezas</span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full border-2 border-primary bg-surface-container-lowest" />
                Blancas (Filas 1-2)
              </span>
            </div>
          )}
        </GlassCard>

        {pasoActual === 1 && (
          <div className="flex items-center justify-center gap-2 text-xs text-on-surface-variant mb-2 overflow-x-auto pb-1">
            {['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'].map((col) => (
              <span key={col} className="w-10 text-center font-bold text-outline">{col}</span>
            ))}
          </div>
        )}

        {pasoActual === 0 && (
          <GlassCard className="bg-primary-container/10 border-primary/20">
            <div className="flex items-center gap-3">
              <CheckCircle size={24} className="text-primary" />
              <div>
                <p className="font-medium text-primary">Clave: Damas en su color</p>
                <p className="text-on-surface-variant text-sm mt-1">
                  d1 = Dama Blanca <span className="font-bold text-primary">(casilla clara)</span> •
                  d8 = Dama Negra <span className="font-bold text-secondary">(casilla oscura)</span>
                </p>
              </div>
            </div>
          </GlassCard>
        )}

        <div className="space-y-3">
          {REGlas_ORO.map((regla, i) => (
            <GlassCard key={i} className={`bg-${regla.color}-container/10 border-${regla.color}/20`}>
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-xl bg-${regla.color}-container flex items-center justify-center flex-shrink-0`}>
                  <regla.icono size={20} className={`text-${regla.color}`} />
                </div>
                <div>
                  <h3 className="font-titulo font-semibold text-on-surface">{regla.titulo}</h3>
                  <p className="text-on-surface-variant text-sm mt-1" dangerouslySetInnerHTML={{__html: regla.mensaje}} />
                </div>
              </div>
            </GlassCard>
          ))}
        </div>

        <GlassCard>
          <h3 className="font-titulo text-lg font-semibold text-on-surface mb-3">Consejo</h3>
          <p className="text-on-surface-variant text-sm">
            Al inicio, todas las piezas están ordenadas y listas para su desarrollo.
            Esta posición inicial es universal y nunca varía en ajedrez estándar.
          </p>
        </GlassCard>

        <div className="flex gap-3">
          <button onClick={handleAnterior} className="flex-1 px-4 py-3 rounded-lg bg-surface-container text-on-surface font-medium hover:bg-surface-container/80 transition-colors">
            Anterior
          </button>
          <BotonPrimario onClick={handleSiguiente} className="flex-1">
            {pasoActual === pasos.length - 1 ? 'Ir al Tutor' : 'Siguiente'}
            <ChevronLeft size={16} className="ml-2 rotate-180" />
          </BotonPrimario>
        </div>
      </main>
    </div>
  );
}