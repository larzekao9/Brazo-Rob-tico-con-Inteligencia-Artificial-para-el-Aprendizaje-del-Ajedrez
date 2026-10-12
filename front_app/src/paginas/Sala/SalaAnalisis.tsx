import {useCallback, useEffect, useState} from 'react';
import {ChevronLeft} from 'lucide-react';
import {analisisSala} from '../../api/sala';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import GlassCard from '../../componentes/GlassCard';
import GraficoEvaluacion from '../../componentes/GraficoEvaluacion';
import HistorialJugadas from '../../componentes/HistorialJugadas';
import {irA, useRuta} from '../../router';
import MomentosClave from './MomentosClave';
import {curvaParaGrafico, esErrorDeConexion, jugadasParaHistorial, mensajeDeError, textoPrecision} from './salaUtil';
import type {AnalisisSala, ErrorApi, ResumenBando} from './tipos';

const MOTIVO_TEXTO = {mate: 'por jaque mate', tablas: 'por tablas', abandono: 'por abandono', inactividad: 'por inactividad'} as const;

function TarjetaBando({titulo, resumen}: {titulo: string; resumen: ResumenBando}) {
  return (
    <GlassCard className="flex flex-1 flex-col gap-1">
      <h3 className="font-titulo text-sm font-bold text-on-surface">{titulo}</h3>
      <p className="truncate text-xs text-on-surface-variant">{resumen.nombre ?? 'Jugador'}</p>
      <p className="font-titulo text-3xl font-bold text-primary">{textoPrecision(resumen.precision)}</p>
      <p className="text-xs text-on-surface-variant">precisión</p>
      <dl className="mt-1 grid grid-cols-2 gap-x-2 text-xs text-on-surface-variant">
        <dt>Mejores</dt>
        <dd className="text-right font-semibold text-on-surface">{resumen.mejores}</dd>
        <dt>Imprecisiones</dt>
        <dd className="text-right font-semibold text-on-surface">{resumen.imprecisiones}</dd>
        <dt>Errores</dt>
        <dd className="text-right font-semibold text-on-surface">{resumen.errores}</dd>
        <dt>Errores graves</dt>
        <dd className="text-right font-semibold text-on-surface">{resumen.blunders}</dd>
      </dl>
    </GlassCard>
  );
}

function titularResultado(analisis: AnalisisSala): string {
  if (analisis.motivo_fin === 'inactividad' || analisis.resultado === null) return 'Partida cancelada por inactividad';
  const motivo = analisis.motivo_fin ? ` ${MOTIVO_TEXTO[analisis.motivo_fin]}` : '';
  if (analisis.resultado === '1/2-1/2') return `Tablas${motivo}`;
  return `Ganaron las ${analisis.resultado === '1-0' ? 'blancas' : 'negras'}${motivo}`;
}

/** /sala/:codigo/analisis: análisis general con Stockfish de los dos bandos (jugadores y espectadores). */
export default function SalaAnalisis() {
  const {params} = useRuta();
  const codigo = params.codigo ?? '';
  const [analisis, setAnalisis] = useState<AnalisisSala | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<{mensaje: string; sinConexion: boolean; aunNoTermina: boolean} | null>(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let activo = true;
    setCargando(true);
    setError(null);
    analisisSala(codigo)
      .then((datos: AnalisisSala) => {
        if (activo) setAnalisis(datos);
      })
      .catch((err: unknown) => {
        if (!activo) return;
        const estado = (err as ErrorApi).status;
        setError({
          mensaje:
            estado === 400
              ? 'La partida todavía no terminó. El análisis estará disponible cuando termine.'
              : estado === 404
                ? 'No existe esa sala.'
                : mensajeDeError(err, 'No se pudo analizar la partida.'),
          sinConexion: esErrorDeConexion(err),
          aunNoTermina: estado === 400,
        });
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => {
      activo = false;
    };
  }, [codigo, intento]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);

  return (
    <section className="flex flex-col gap-4 p-4 pb-8">
      <header className="flex items-center gap-2">
        <button type="button" onClick={() => irA('/inicio')} aria-label="Volver al inicio" className="flex size-11 items-center justify-center rounded-full text-on-surface hover:bg-surface-container">
          <ChevronLeft size={24} aria-hidden="true" />
        </button>
        <div className="min-w-0">
          <h1 className="font-titulo text-xl font-bold text-on-surface">Análisis de la partida</h1>
          <p className="text-xs text-on-surface-variant">Sala {codigo}</p>
        </div>
      </header>

      {cargando && <Cargando mensaje="Analizando con Stockfish… puede tardar unos segundos" />}

      {!cargando && error && (
        <>
          <ErrorReintentar mensaje={error.mensaje} onReintentar={error.sinConexion || !error.aunNoTermina ? reintentar : undefined} />
          <BotonPrimario variante="secundario" onClick={() => irA('/sala/:codigo', {codigo})}>
            Volver a la sala
          </BotonPrimario>
        </>
      )}

      {!cargando && analisis && (
        <>
          <GlassCard className="bg-primary-container">
            <h2 className="font-titulo text-lg font-bold text-on-primary-container">{titularResultado(analisis)}</h2>
            <p className="text-sm text-on-primary-container">{analisis.total_jugadas} jugadas analizadas</p>
          </GlassCard>

          {analisis.total_jugadas === 0 ? (
            <p className="text-sm text-on-surface-variant">No se jugó ninguna jugada: no hay nada que analizar.</p>
          ) : (
            <>
              <div className="flex gap-3">
                <TarjetaBando titulo="Blancas" resumen={analisis.blancas} />
                <TarjetaBando titulo="Negras" resumen={analisis.negras} />
              </div>

              <GlassCard className="flex flex-col gap-2">
                <h2 className="font-titulo text-base font-bold text-on-surface">Evaluación de la partida</h2>
                <p className="text-xs text-on-surface-variant">Arriba, ventaja de las blancas; abajo, de las negras.</p>
                <GraficoEvaluacion evaluaciones={curvaParaGrafico(analisis.curva)} />
              </GlassCard>

              <section aria-labelledby="titulo-momentos" className="flex flex-col gap-3">
                <h2 id="titulo-momentos" className="font-titulo text-base font-bold text-on-surface">
                  Momentos clave
                </h2>
                <MomentosClave momentos={analisis.momentos_clave} jugadas={analisis.jugadas} />
              </section>

              <GlassCard>
                <h2 className="mb-2 font-titulo text-base font-bold text-on-surface">Jugada por jugada</h2>
                <HistorialJugadas jugadas={jugadasParaHistorial(analisis.jugadas)} />
              </GlassCard>
            </>
          )}

          <BotonPrimario variante="secundario" onClick={() => irA('/sala/:codigo', {codigo})}>
            Ver el tablero
          </BotonPrimario>
          <BotonPrimario onClick={() => irA('/inicio')}>Volver al inicio</BotonPrimario>
        </>
      )}
    </section>
  );
}
