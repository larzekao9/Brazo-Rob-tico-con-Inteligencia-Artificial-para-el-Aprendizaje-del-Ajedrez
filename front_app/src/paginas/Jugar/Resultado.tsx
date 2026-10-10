import {useCallback, useEffect, useMemo, useState, type ReactNode} from 'react';
import {BarChart3, Home, RotateCcw, Star, Target, TrendingDown, TrendingUp, Trophy} from 'lucide-react';
import {analisisCompletoPartida, calibrarPartida, obtenerPartida} from '../../api/backend';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import Chip from '../../componentes/Chip';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import GlassCard from '../../componentes/GlassCard';
import GraficoEvaluacion from '../../componentes/GraficoEvaluacion';
import HistorialJugadas from '../../componentes/HistorialJugadas';
import {describirCambioNivel, precisionAPorcentaje} from '../../dominio/nivelJugador';
import {useSesion} from '../../estado/SesionContext';
import {irA, useRuta} from '../../router';
import {
  curvaDeEvaluacion,
  jugadasParaHistorial,
  peoresErrores,
  textoEvaluacionFinal,
  type AnalisisCompleto,
  type Calibracion,
} from './datosResultado';
import ListaErrores from './ListaErrores';
import {colorDelJugador, veredictoDe, type EstadoPartida, type Veredicto} from './partidaUtil';
import {OPONENTES, type TipoOponente} from './seleccion';

const TITULOS: Record<Veredicto, {titulo: string; frase: string}> = {
  victoria: {titulo: '¡Victoria!', frase: 'Cada partida es una oportunidad para ser mejor.'},
  derrota: {titulo: '¡Buen intento!', frase: 'Las derrotas también forman parte del progreso.'},
  tablas: {titulo: 'Tablas', frase: 'Un empate también se aprende.'},
};

// Stockfish analiza cada jugada y tarda unos segundos; en dev React monta dos veces, así que se comparte la promesa.
const analisisEnCurso = new Map<string, Promise<AnalisisCompleto>>();

function pedirAnalisis(id: string, rango: string | null): Promise<AnalisisCompleto> {
  const existente = analisisEnCurso.get(id);
  if (existente) return existente;
  const nuevo = (analisisCompletoPartida(id, rango ?? undefined) as Promise<AnalisisCompleto>).catch((err) => {
    analisisEnCurso.delete(id);
    throw err;
  });
  analisisEnCurso.set(id, nuevo);
  return nuevo;
}

function Metrica({icono, etiqueta, valor, nota}: {icono: ReactNode; etiqueta: string; valor: string; nota?: string}) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1 px-1 text-center">
      {icono}
      <span className="text-xs text-on-surface-variant">{etiqueta}</span>
      <span className="font-titulo text-2xl font-bold text-on-surface">{valor}</span>
      {nota && <span className="text-xs text-on-surface-variant">{nota}</span>}
    </div>
  );
}

export default function Resultado() {
  const {params} = useRuta();
  const id = params.id ?? '';
  const {usuario, recargarUsuario, cargarEstadisticas} = useSesion();
  const [partida, setPartida] = useState<EstadoPartida | null>(null);
  const [analisis, setAnalisis] = useState<AnalisisCompleto | null>(null);
  const [calibracion, setCalibracion] = useState<Calibracion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const rango = usuario?.rango_estimado ?? null;

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    setPartida(null);
    setAnalisis(null);
    setCalibracion(null);
    try {
      setPartida((await obtenerPartida(id)) as EstadoPartida);
      const datos = await pedirAnalisis(id, rango);
      setAnalisis(datos);
      // El análisis ya calibra el nivel (idempotente por partida); se pide aparte solo si el backend no lo informó.
      setCalibracion(datos.calibracion ?? ((await calibrarPartida(id)) as Calibracion));
      await Promise.all([recargarUsuario(), cargarEstadisticas()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo analizar la partida.');
    } finally {
      setCargando(false);
    }
    // `rango` solo se lee al abrir: recargar el usuario lo cambia y no debe relanzar el análisis.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const jugadas = useMemo(() => analisis?.jugadas ?? [], [analisis]);
  const errores = useMemo(() => peoresErrores(jugadas), [jugadas]);

  const color = partida ? colorDelJugador(partida.fen_inicial) : 'w';
  const veredicto = partida ? veredictoDe(partida.resultado, color) : null;
  const textos = veredicto ? TITULOS[veredicto] : {titulo: 'Partida terminada', frase: ''};
  const oponente = partida ? (OPONENTES[partida.tipo_oponente as TipoOponente]?.titulo ?? partida.tipo_oponente) : '';
  const precision = precisionAPorcentaje(analisis?.resumen?.precision_jugador ?? calibracion?.precision_partida);
  const promedio = precisionAPorcentaje(calibracion?.precision_promedio);
  const diferencia = precision !== null && promedio !== null ? precision - promedio : null;
  const cambioNivel = calibracion?.registrada ? describirCambioNivel(calibracion) : null;
  const jugadasDelJugador = jugadas.filter((j) => j.quien === 'jugador').length;

  return (
    <section className="flex flex-col gap-4 p-4 pb-8">
      <header className="flex items-center gap-4">
        <span aria-hidden="true" className={`flex size-20 shrink-0 items-center justify-center rounded-full ${veredicto === 'victoria' ? 'bg-primary-container text-primary' : 'bg-surface-highest text-inverse-surface'}`}>
          <Trophy size={40} />
        </span>
        <div>
          <h1 className="font-titulo text-3xl font-bold text-on-surface">{textos.titulo}</h1>
          {partida && (
            <p className="text-sm text-on-surface-variant">
              {veredicto === 'victoria' && `Ganaste contra ${oponente}.`}
              {veredicto === 'derrota' && `En esta partida ganó ${oponente}.`}
              {veredicto === 'tablas' && `Empataste contra ${oponente}.`}
              {!veredicto && `Resultado: ${partida.resultado ?? '—'}`}
            </p>
          )}
          <p className="text-xs italic text-on-surface-variant">{textos.frase}</p>
        </div>
      </header>

      {cargando && <Cargando mensaje="Analizando la partida con Stockfish… puede tardar unos segundos." />}
      {error && <ErrorReintentar mensaje={error} onReintentar={() => void cargar()} />}

      {analisis && (
        <>
          {cambioNivel && (
            <GlassCard className={`flex items-center gap-3 ${cambioNivel.sube ? 'bg-primary-container text-on-primary-container' : 'bg-tertiary-container text-on-tertiary-container'}`}>
              {cambioNivel.sube ? <TrendingUp size={24} aria-hidden="true" /> : <TrendingDown size={24} aria-hidden="true" />}
              <p className="text-sm font-semibold">
                {cambioNivel.principal} ({cambioNivel.detalle})
              </p>
            </GlassCard>
          )}
          {calibracion?.registrada && calibracion.es_diagnostico && calibracion.nivel != null && (
            <GlassCard className="bg-secondary-container text-on-secondary-container">
              <p className="text-sm font-semibold">Tu nivel medido es {calibracion.nivel}{calibracion.rango ? ` (${calibracion.rango})` : ''}.</p>
            </GlassCard>
          )}

          <GlassCard className="flex divide-x divide-outline-variant">
            <Metrica
              icono={<Target size={26} className="text-secondary" aria-hidden="true" />}
              etiqueta="Precisión"
              valor={precision !== null ? `${precision}%` : '—'}
              nota={diferencia !== null && diferencia !== 0 ? `${diferencia > 0 ? '+' : ''}${diferencia}% vs. tu promedio` : undefined}
            />
            <Metrica icono={<BarChart3 size={26} className="text-primary" aria-hidden="true" />} etiqueta="Movimientos" valor={String(jugadasDelJugador)} nota="tuyos" />
            <Metrica icono={<Star size={26} className="text-tertiary" aria-hidden="true" />} etiqueta="Evaluación final" valor={textoEvaluacionFinal(jugadas)} nota={color === 'w' ? 'desde las blancas' : undefined} />
          </GlassCard>

          <GlassCard className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <h2 className="font-titulo text-lg font-bold text-on-surface">Evolución de la partida</h2>
              {partida?.resultado && <Chip tono={veredicto === 'victoria' ? 'primario' : veredicto === 'derrota' ? 'error' : 'neutro'}>{partida.resultado}</Chip>}
            </div>
            <GraficoEvaluacion evaluaciones={curvaDeEvaluacion(jugadas)} />
            <p className="text-xs text-on-surface-variant">Arriba: ventaja de las blancas. Abajo: ventaja de las negras.</p>
          </GlassCard>

          <ListaErrores errores={errores} consejo={analisis.resumen?.consejo_tutor} />

          <details className="rounded-tarjeta border border-glass-border bg-glass p-4">
            <summary className="cursor-pointer font-titulo text-base font-bold text-on-surface">Revisar análisis jugada por jugada</summary>
            <div className="mt-3">
              <HistorialJugadas jugadas={jugadasParaHistorial(jugadas)} />
            </div>
          </details>
        </>
      )}

      <div className="flex flex-col gap-2">
        <BotonPrimario onClick={() => irA('/jugar')}>
          <RotateCcw size={18} aria-hidden="true" /> Jugar de nuevo
        </BotonPrimario>
        <BotonPrimario variante="secundario" onClick={() => irA('/inicio')}>
          <Home size={18} aria-hidden="true" /> Volver al inicio
        </BotonPrimario>
      </div>
    </section>
  );
}
