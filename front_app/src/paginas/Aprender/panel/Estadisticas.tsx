import {useEffect, useState, type ReactNode} from 'react';
import {Flame, Target, Trophy, Gamepad2, TrendingDown, Minus, TrendingUp} from 'lucide-react';
import {obtenerEstadisticasUsuario} from '../../../api/extra';
import ErrorReintentar from '../../../componentes/ErrorReintentar';
import GlassCard from '../../../componentes/GlassCard';
import ProgresoBarra from '../../../componentes/ProgresoBarra';
import {CargandoInline, Vacio} from './ui';

interface Semana {
  semana_inicio: string;
  partidas: number;
  victorias: number;
  precision: number | null;
}
interface Resultados {
  ganadas: number;
  perdidas: number;
  tablas: number;
}
interface Fase {
  fase: string;
  jugadas: number;
  precision: number | null;
}
interface DatosEstadisticas {
  partidas_ganadas: number;
  partidas_perdidas: number;
  partidas_tablas: number;
  win_percent_promedio: number;
  racha_victoria_actual: number;
  precision_promedio: number;
  top_errores?: {tipo: string; cantidad: number}[];
  partidas_por_oponente?: {motor?: number; modelo?: number};
  progreso_semanal?: Semana[];
  resultados_por_oponente?: {motor?: Resultados; modelo?: Resultados};
  precision_por_fase?: Fase[];
}

/** Mínimo de partidas jugadas para mostrar "errores más frecuentes": con menos no hay patrón. */
const PARTIDAS_PARA_TOP_ERRORES = 3;
/** Con menos jugadas analizadas que esto, el porcentaje de una fase no dice nada. */
const MINIMO_JUGADAS_POR_FASE = 3;

const NOMBRE_ERROR: Record<string, {titulo: string; detalle: string; barra: string}> = {
  blunder: {titulo: 'Blunders', detalle: 'regalar una pieza o permitir un mate', barra: 'bg-error'},
  error: {titulo: 'Errores', detalle: 'ceder una ventaja apreciable', barra: 'bg-tertiary'},
  inexactitud: {titulo: 'Inexactitudes', detalle: 'una jugada algo peor que la mejor', barra: 'bg-secondary'},
};
const NOMBRE_FASE: Record<string, string> = {apertura: 'Apertura', medio: 'Medio juego', final: 'Final'};
const CON_ARTICULO: Record<string, string> = {apertura: 'la apertura', medio: 'el medio juego', final: 'el final'};
const CONSEJO_FASE: Record<string, string> = {
  apertura: 'Repasa los principios de la apertura: controla el centro, saca las piezas y enroca pronto.',
  medio: 'Antes de cada jugada revisa qué amenaza el rival y si dejas alguna pieza sin defensa.',
  final: 'Practica finales sencillos: acerca el rey, avanza los peones y activa las torres.',
};

/** Compara esta semana con la anterior: por precisión si ambas tienen jugadas analizadas, si no por cantidad de partidas. */
export function compararConSemanaAnterior(semanas: Semana[] | undefined): {tono: 'sube' | 'baja' | 'igual'; texto: string} | null {
  if (!Array.isArray(semanas) || semanas.length < 2) return null;
  const actual = semanas[semanas.length - 1];
  const anterior = semanas[semanas.length - 2];
  if (actual.precision != null && anterior.precision != null) {
    const dif = Math.round((actual.precision - anterior.precision) * 10) / 10;
    if (dif > 0) return {tono: 'sube', texto: `Mejoraste ${dif} puntos de precisión respecto a la semana pasada.`};
    if (dif < 0) return {tono: 'baja', texto: `Bajaste ${Math.abs(dif)} puntos de precisión respecto a la semana pasada.`};
    return {tono: 'igual', texto: 'Tu precisión se mantuvo igual que la semana pasada.'};
  }
  if (actual.partidas > 0 || anterior.partidas > 0) {
    return {tono: 'igual', texto: `Esta semana jugaste ${actual.partidas} ${actual.partidas === 1 ? 'partida' : 'partidas'} y la anterior ${anterior.partidas}.`};
  }
  return null;
}

/** La fase con menor precisión entre las que tienen datos suficientes, o null si no hay con qué comparar. */
export function faseMasFloja(fases: Fase[] | undefined): Fase | null {
  const medibles = (fases ?? []).filter((f) => f.precision != null && f.jugadas >= MINIMO_JUGADAS_POR_FASE);
  if (medibles.length < 2) return null;
  return medibles.reduce((peor, f) => ((f.precision ?? 0) < (peor.precision ?? 0) ? f : peor));
}

const diaMes = (iso: string) => `${iso.split('-')[2]}/${iso.split('-')[1]}`;

function Indicador({icono, titulo, valor, detalle}: {icono: ReactNode; titulo: string; valor: string | number; detalle: string}) {
  return (
    <GlassCard className="flex min-w-0 flex-col gap-1">
      <span className="flex items-center gap-1 text-xs font-semibold text-on-surface-variant">
        <span className="text-primary" aria-hidden="true">
          {icono}
        </span>
        {titulo}
      </span>
      <span className="font-titulo text-2xl font-bold text-on-surface">{valor}</span>
      <span className="break-words text-xs text-on-surface-variant">{detalle}</span>
    </GlassCard>
  );
}

function Bloque({titulo, children}: {titulo: string; children: ReactNode}) {
  return (
    <GlassCard className="flex flex-col gap-3">
      <h3 className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">{titulo}</h3>
      {children}
    </GlassCard>
  );
}

/** Barra apilada de ganadas / tablas / perdidas, con los números escritos al lado (el color no es lo único que informa). */
function BarraResultados({r}: {r: Resultados}) {
  const total = r.ganadas + r.tablas + r.perdidas;
  if (total === 0) return <p className="text-xs text-on-surface-variant">Sin partidas terminadas.</p>;
  const tramos = [
    {clave: 'ganadas', valor: r.ganadas, clase: 'bg-primary'},
    {clave: 'tablas', valor: r.tablas, clase: 'bg-secondary'},
    {clave: 'perdidas', valor: r.perdidas, clase: 'bg-error'},
  ];
  return (
    <div className="flex flex-col gap-1">
      <div className="flex h-4 overflow-hidden rounded-full bg-surface-highest" role="img" aria-label={`${r.ganadas} ganadas, ${r.tablas} tablas, ${r.perdidas} perdidas`}>
        {tramos.map((t) => t.valor > 0 && <span key={t.clave} className={`${t.clase} h-full`} style={{width: `${(t.valor / total) * 100}%`}} />)}
      </div>
      <p className="text-xs text-on-surface-variant">
        {r.ganadas} ganadas · {r.tablas} tablas · {r.perdidas} perdidas ({Math.round((r.ganadas / total) * 100)}% de victorias)
      </p>
    </div>
  );
}

function ProgresoSemanal({semanas}: {semanas: Semana[]}) {
  const [rango, setRango] = useState(4);
  const lista = semanas.slice(-rango);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2" role="group" aria-label="Período">
        {[4, 8].map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={rango === n}
            onClick={() => setRango(n)}
            className={`min-h-9 rounded-full border px-3 text-xs font-semibold ${rango === n ? 'border-primary bg-primary-container text-on-primary-container' : 'border-outline-variant text-on-surface-variant'}`}
          >
            {n} semanas
          </button>
        ))}
      </div>
      <ul className="flex flex-col gap-2">
        {lista.map((s) => (
          <li key={s.semana_inicio} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between text-xs">
              <span className="font-semibold text-on-surface">Semana del {diaMes(s.semana_inicio)}</span>
              <span className="text-on-surface-variant">
                {s.partidas === 0 ? 'sin partidas' : `${s.partidas} ${s.partidas === 1 ? 'partida' : 'partidas'} · ${s.victorias} ${s.victorias === 1 ? 'victoria' : 'victorias'} · ${s.precision == null ? 'sin precisión medida' : `${s.precision}%`}`}
              </span>
            </div>
            <ProgresoBarra valor={s.precision ?? 0} etiqueta={undefined} tono="cian" />
          </li>
        ))}
      </ul>
      <p className="text-xs text-on-surface-variant">Cada barra es la precisión de la semana (0 a 100).</p>
    </div>
  );
}

function PrecisionPorFase({fases}: {fases: Fase[]}) {
  if (fases.every((f) => f.jugadas === 0)) return <p className="text-sm text-on-surface-variant">Cuando se analicen tus partidas terminadas, acá vas a ver en qué fase juegas mejor.</p>;
  const floja = faseMasFloja(fases);
  return (
    <div className="flex flex-col gap-3">
      {fases.map((f) => (
        <div key={f.fase}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="font-semibold text-on-surface">{NOMBRE_FASE[f.fase] ?? f.fase}</span>
            <span className="text-on-surface-variant">{f.precision == null ? 'sin jugadas analizadas' : `${f.precision}% · ${f.jugadas} jugadas`}</span>
          </div>
          <ProgresoBarra valor={f.precision ?? 0} tono="primario" />
        </div>
      ))}
      <p className="text-sm text-on-surface" role="status">
        {floja ? `Tu fase más floja es ${CON_ARTICULO[floja.fase] ?? floja.fase} (${floja.precision}%). ${CONSEJO_FASE[floja.fase] ?? ''}` : 'Juega y analiza más partidas para comparar tus fases.'}
      </p>
    </div>
  );
}

/** Estadísticas personales (HU14): las calcula el backend en GET /usuario/estadisticas; acá solo se presentan. */
export default function Estadisticas() {
  const [datos, setDatos] = useState<DatosEstadisticas | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [cargando, setCargando] = useState(true);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    obtenerEstadisticasUsuario()
      .then((r: DatosEstadisticas) => vigente && setDatos(r))
      .catch((err: Error) => vigente && setError(err))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [intento]);

  if (cargando) return <CargandoInline texto="Calculando tus estadísticas…" />;
  if (error) return <ErrorReintentar mensaje={error.message || 'No se pudieron cargar tus estadísticas.'} onReintentar={() => setIntento((n) => n + 1)} />;
  if (!datos) return null;

  const porOponente = datos.partidas_por_oponente ?? {};
  const jugadas = (porOponente.motor ?? 0) + (porOponente.modelo ?? 0);
  if (jugadas === 0) return <Vacio>Todavía no jugaste ninguna partida. Juega una y acá vas a ver tu progreso.</Vacio>;

  const comparacion = compararConSemanaAnterior(datos.progreso_semanal);
  const errores = (datos.top_errores ?? []).slice(0, 3);
  const totalErrores = errores.reduce((suma, e) => suma + e.cantidad, 0);
  const mayorError = Math.max(1, ...errores.map((e) => e.cantidad));
  const finalizadas = datos.partidas_ganadas + datos.partidas_perdidas + datos.partidas_tablas;
  const ResultadoVacio: Resultados = {ganadas: 0, perdidas: 0, tablas: 0};
  const Tendencia = comparacion?.tono === 'sube' ? TrendingUp : comparacion?.tono === 'baja' ? TrendingDown : Minus;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <Indicador icono={<Gamepad2 size={14} />} titulo="Partidas jugadas" valor={jugadas} detalle={`Turing: ${porOponente.modelo ?? 0} · Stockfish: ${porOponente.motor ?? 0}`} />
        <Indicador
          icono={<Trophy size={14} />}
          titulo="Victorias"
          valor={finalizadas ? `${datos.win_percent_promedio}%` : '—'}
          detalle={`${datos.partidas_ganadas} ganadas · ${datos.partidas_perdidas} perdidas · ${datos.partidas_tablas} tablas`}
        />
        <Indicador icono={<Target size={14} />} titulo="Precisión" valor={datos.precision_promedio > 0 ? `${datos.precision_promedio}%` : '—'} detalle="Jugadas a menos de medio peón de la mejor" />
        <Indicador
          icono={<Flame size={14} />}
          titulo="Racha de victorias"
          valor={datos.racha_victoria_actual}
          detalle={datos.racha_victoria_actual === 1 ? 'partida ganada seguida' : 'partidas ganadas seguidas'}
        />
      </div>

      {comparacion && (
        <p className={`flex items-center gap-2 rounded-2xl p-3 text-sm ${comparacion.tono === 'sube' ? 'bg-primary-container text-on-primary-container' : comparacion.tono === 'baja' ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-surface-container text-on-surface'}`}>
          <Tendencia size={18} className="shrink-0" aria-hidden="true" />
          {comparacion.texto}
        </p>
      )}

      {(datos.progreso_semanal?.length ?? 0) > 0 && (
        <Bloque titulo="Tu progreso por semana">
          <ProgresoSemanal semanas={datos.progreso_semanal ?? []} />
        </Bloque>
      )}

      <Bloque titulo="Tu precisión por fase de la partida">
        <PrecisionPorFase fases={datos.precision_por_fase ?? []} />
      </Bloque>

      <Bloque titulo="Tus resultados">
        <BarraResultados r={{ganadas: datos.partidas_ganadas, perdidas: datos.partidas_perdidas, tablas: datos.partidas_tablas}} />
      </Bloque>

      <Bloque titulo="Cómo te fue con cada rival">
        <div className="flex flex-col gap-3">
          <div>
            <p className="mb-1 text-xs font-semibold text-on-surface">Contra Turing</p>
            <BarraResultados r={datos.resultados_por_oponente?.modelo ?? ResultadoVacio} />
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold text-on-surface">Contra Stockfish</p>
            <BarraResultados r={datos.resultados_por_oponente?.motor ?? ResultadoVacio} />
          </div>
        </div>
      </Bloque>

      <Bloque titulo="Tus errores más frecuentes">
        {jugadas < PARTIDAS_PARA_TOP_ERRORES ? (
          <p className="text-sm text-on-surface-variant">
            Juega al menos {PARTIDAS_PARA_TOP_ERRORES} partidas para ver en qué te equivocas más seguido (llevas {jugadas}).
          </p>
        ) : errores.length === 0 ? (
          <p className="text-sm text-on-surface-variant">Todavía no hay errores analizados.</p>
        ) : (
          <ol className="flex flex-col gap-3">
            {errores.map((e, i) => {
              const nombre = NOMBRE_ERROR[e.tipo] ?? {titulo: e.tipo, detalle: '', barra: 'bg-primary'};
              return (
                <li key={e.tipo} className="flex flex-col gap-1">
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="min-w-0 text-on-surface">
                      <span className="mr-1 text-xs font-bold text-primary">{i + 1}.</span>
                      <strong>{nombre.titulo}</strong>
                      {nombre.detalle && <span className="text-on-surface-variant"> · {nombre.detalle}</span>}
                    </span>
                    <span className="shrink-0 font-titulo font-bold text-on-surface">
                      {e.cantidad} <span className="text-xs font-normal text-on-surface-variant">({Math.round((e.cantidad / totalErrores) * 100)}%)</span>
                    </span>
                  </div>
                  <span className="block h-2 overflow-hidden rounded-full bg-surface-highest" aria-hidden="true">
                    <span className={`block h-full rounded-full ${nombre.barra}`} style={{width: `${(e.cantidad / mayorError) * 100}%`}} />
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </Bloque>
    </div>
  );
}
