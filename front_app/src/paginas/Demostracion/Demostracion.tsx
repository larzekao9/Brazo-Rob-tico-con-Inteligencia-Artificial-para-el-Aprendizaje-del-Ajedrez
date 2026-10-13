import {useEffect, useState} from 'react';
import {ChevronLeft, Radio, Wifi, WifiOff, Loader2, Eye, EyeOff, RotateCcw} from 'lucide-react';
import {irA, useRuta} from '../../router';
import {useSesion} from '../../estado/SesionContext';
import {obtenerDemostracionActiva, obtenerPartida} from '../../api/backend';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import TableroDemo from '../../componentes/TableroDemo';

interface DemostracionActiva {
  id: number;
  fen_actual: string;
  turno: 'w' | 'b';
  jugadas: string[];
  ultima_actualizacion: string;
}

export default function Demostracion() {
  const {usuario} = useSesion();
  const {ruta} = useRuta();
  const [demo, setDemo] = useState<DemostracionActiva | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sondeando, setSondeando] = useState(false);
  const [orientacion, setOrientacion] = useState<'w' | 'b'>('w');
  const [mostrarJugadas, setMostrarJugadas] = useState(true);

  useEffect(() => {
    let activo = true;
    let intervalo: ReturnType<typeof setInterval>;

    const sondear = async () => {
      if (sondeando) return;
      setSondeando(true);
      try {
        const data = await obtenerDemostracionActiva();
        if (activo) {
          if (data) {
            setDemo({
              id: data.id,
              fen_actual: data.fen_actual || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
              turno: data.turno || 'w',
              jugadas: data.jugadas || [],
              ultima_actualizacion: data.ultima_actualizacion || new Date().toISOString(),
            });
            setError(null);
          } else {
            setDemo(null);
            setError('No hay ninguna demostración en vivo en este momento.');
          }
        }
      } catch (err: any) {
        if (activo) {
          setError(err.message || 'Error conectando con la demostración');
          setDemo(null);
        }
      } finally {
        if (activo) setSondeando(false);
      }
    };

    sondear();
    intervalo = setInterval(sondear, 2500);

    return () => {
      activo = false;
      clearInterval(intervalo);
    };
  }, [sondeando]);

  const handleVolver = () => irA('/inicio');

  const handleRefrescar = () => {
    setSondeando(false);
  };

  const getTurnoTexto = (turno: 'w' | 'b') => turno === 'w' ? 'Blancas' : 'Negras';
  const getTurnoColor = (turno: 'w' | 'b') => turno === 'w' ? 'text-primary' : 'text-secondary';

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur-md border-b border-outline-variant px-4 py-3">
        <div className="flex items-center justify-between">
          <button onClick={handleVolver} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
          <div className="flex-1 text-center">
            <p className="text-xs font-medium text-primary tracking-wide">INICIO</p>
            <h1 className="font-titulo text-xl font-bold text-on-surface">Demostración en vivo</h1>
          </div>
          <button onClick={handleRefrescar} disabled={sondeando} className="p-2 rounded-full hover:bg-surface-container disabled:opacity-50 transition-colors" aria-label="Refrescar">
            {sondeando ? <Loader2 size={20} className="animate-spin" /> : <RotateCcw size={20} />}
          </button>
        </div>
        {demo && (
          <div className="px-4 pb-3 border-b border-outline-variant">
            <div className="flex items-center justify-between text-sm">
              <span className={`font-medium ${getTurnoColor(demo.turno)}`}>
                Turno: {getTurnoTexto(demo.turno)}
              </span>
              <span className="flex items-center gap-1 text-on-surface-variant">
                <Wifi size={14} className="text-primary" />
                En vivo
              </span>
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 p-4 space-y-4 overflow-y-auto">
        {cargando ? (
          <div className="flex-1 flex items-center justify-center">
            <Cargando mensaje="Buscando demostración activa…" />
          </div>
        ) : error && !demo ? (
          <GlassCard className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-error-container/30 flex items-center justify-center mx-auto mb-4">
              <WifiOff size={32} className="text-error" />
            </div>
            <h2 className="font-titulo text-xl font-bold text-on-surface mb-2">Sin demostración activa</h2>
            <p className="text-on-surface-variant mb-6 max-w-md mx-auto">{error}</p>
            <div className="flex gap-3 justify-center">
              <button onClick={handleRefrescar} disabled={sondeando} className="px-4 py-2.5 rounded-lg bg-primary text-on-primary font-medium disabled:opacity-50">
                {sondeando ? <Loader2 size={18} className="animate-spin" /> : 'Reintentar'}
              </button>
              <BotonPrimario onClick={handleVolver} variante="secundario">
                Volver al inicio
              </BotonPrimario>
            </div>
          </GlassCard>
        ) : demo ? (
          <>
            <GlassCard>
              <div className="relative aspect-square max-w-md mx-auto">
                <TableroDemo
                  fen={demo.fen_actual}
                  orientacion={orientacion}
                  ariaLabel={`Tablero de demostración en vivo - Partida #${demo.id}`}
                />
                <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
                  <button
                    onClick={() => setOrientacion(orientacion === 'w' ? 'b' : 'w')}
                    className="p-2 rounded-full bg-surface-container/90 backdrop-blur-sm shadow-md text-on-surface hover:bg-surface-container transition-colors"
                    aria-label={orientacion === 'w' ? 'Ver desde Negras' : 'Ver desde Blancas'}
                  >
                    {orientacion === 'w' ? '↻' : '↺'}
                  </button>
                  <button
                    onClick={() => setMostrarJugadas(!mostrarJugadas)}
                    className="px-3 py-1.5 rounded-full bg-surface-container/90 backdrop-blur-sm shadow-md text-on-surface text-sm font-medium hover:bg-surface-container transition-colors"
                    aria-label={mostrarJugadas ? 'Ocultar jugadas' : 'Mostrar jugadas'}
                  >
                    {mostrarJugadas ? <EyeOff size={16} /> : <Eye size={16} />}
                    {' '}{mostrarJugadas ? 'Ocultar' : 'Ver'} jugadas
                  </button>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-center gap-4 text-sm text-on-surface-variant">
                <span className="flex items-center gap-1">
                  <Radio size={14} className="text-primary" />
                  Partida #{demo.id}
                </span>
                <span className="flex items-center gap-1">
                  <Loader2 size={14} className="text-secondary" />
                  Actualizado: {new Date(demo.ultima_actualizacion).toLocaleTimeString('es-ES')}
                </span>
              </div>
            </GlassCard>

            {mostrarJugadas && demo.jugadas.length > 0 && (
              <GlassCard>
                <h3 className="font-titulo font-semibold text-on-surface mb-3">Historial de jugadas</h3>
                <div className="max-h-60 overflow-y-auto">
                  <table className="w-full text-sm">
                    <tbody>
                      {demo.jugadas.map((jugada, i) => {
                        const num = Math.floor(i / 2) + 1;
                        const esBlanca = i % 2 === 0;
                        return (
                          <tr key={i} className="hover:bg-surface-container/50">
                            <td className="w-12 text-right pr-2 font-medium text-on-surface-variant">
                              {esBlanca ? `${num}.` : ''}
                            </td>
                            <td className="w-1/2 px-2">{esBlanca ? jugada : ''}</td>
                            <td className="w-1/2 px-2">{!esBlanca ? jugada : ''}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            )}

            {(!demo.jugadas.length || demo.jugadas.length === 0) && (
              <GlassCard className="text-center py-6">
                <p className="text-on-surface-variant">La demostración acaba de empezar. Las jugadas aparecerán aquí conforme se jueguen.</p>
              </GlassCard>
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}