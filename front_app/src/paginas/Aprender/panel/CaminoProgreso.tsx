import {useEffect, useMemo, useState} from 'react';
import {Check, Flame, Lock} from 'lucide-react';
import {historialPartidasPropio, obtenerPartida} from '../../../api/backend';
import BotonPrimario from '../../../componentes/BotonPrimario';
import ErrorReintentar from '../../../componentes/ErrorReintentar';
import {rutaImagenPieza} from '../../../dominio/ajedrez';
import {irA} from '../../../router';
import {cargarCapitulosVistos, guardarCapitulosVistos} from './prefs';
import {CargandoInline} from './ui';

/** Cuántas partidas recientes se revisan para los capítulos de captura y jaque, y cuántas se piden juntas. */
const PARTIDAS_A_REVISAR = 20;
const LOTE_DE_PARTIDAS = 4;

type Accion = {tipo: 'ruta'; ruta: string; texto: string} | {tipo: 'piezas'; texto: string};

interface Capitulo {
  id: string;
  titulo: string;
  descripcion: string;
  /** Letra FEN de la pieza que lo representa. */
  pieza: string;
  /** El propio jugador lo marca como visto (no se puede medir con partidas). */
  marcable?: boolean;
  accion?: Accion;
}

/**
 * Capítulos del camino para quien está aprendiendo las bases. Tablero, piezas, captura y jaque se completan con
 * datos reales (partidas del jugador o piezas vistas); posición y movimientos los marca el propio jugador.
 */
const CAPITULOS: Capitulo[] = [
  {id: 'tablero', titulo: 'El tablero', pieza: 'P', descripcion: 'Cómo está armado el tablero. Se completa al jugar tu primera partida.', accion: {tipo: 'ruta', ruta: '/aprender/tablero', texto: 'Ver la lección del tablero'}},
  {id: 'piezas', titulo: 'Las piezas', pieza: 'Q', descripcion: 'Conoce las 6 piezas y cómo se mueve cada una. Se completa al revisarlas todas en "Aprende cada pieza".', accion: {tipo: 'piezas', texto: 'Ir a Aprende cada pieza'}},
  {id: 'posicion', titulo: 'Posición inicial', pieza: 'R', marcable: true, descripcion: 'Dónde empieza cada pieza en el tablero. Márcala como vista cuando la termines.', accion: {tipo: 'ruta', ruta: '/aprender/posicion-inicial', texto: 'Ver la lección'}},
  {id: 'movimientos', titulo: 'Movimiento de las piezas', pieza: 'N', marcable: true, descripcion: 'Cómo se mueve cada pieza en su turno. Márcala como vista cuando la termines.', accion: {tipo: 'ruta', ruta: '/aprender/piezas', texto: 'Ver la lección'}},
  {id: 'captura', titulo: 'Captura de piezas', pieza: 'B', descripcion: 'Cuándo una pieza captura a otra. Se completa cuando haces una captura en una de tus partidas.', accion: {tipo: 'ruta', ruta: '/jugar', texto: 'Ir a jugar'}},
  {id: 'jaque', titulo: 'Jaque y jaque mate', pieza: 'K', descripcion: 'Cómo dar jaque y jaque mate. Se completa cuando das jaque o mate en una de tus partidas.', accion: {tipo: 'ruta', ruta: '/jugar', texto: 'Ir a jugar'}},
];

/** Capítulos previstos que todavía no tienen contenido: se muestran sin progreso. */
const PROXIMOS = ['Estrategias básicas', 'Puzzles y práctica'];

type Estado = 'completado' | 'en_curso' | 'bloqueado';

/** El jugador lleva blancas: sus jugadas son las de índice par de `jugadas_san`. */
const jugadasDelJugador = (jugadasSan: string[]) => jugadasSan.filter((_, i) => i % 2 === 0);
const hizoCaptura = (jugadasSan: string[]) => jugadasDelJugador(jugadasSan).some((san) => san.includes('x'));
const dioJaque = (jugadasSan: string[]) => jugadasDelJugador(jugadasSan).some((san) => san.includes('+') || san.includes('#'));

/** Días seguidos con al menos una partida, contando hoy (o ayer, si hoy todavía no jugó). */
function rachaDeDias(fechas: string[], ahora = new Date()): number {
  const clave = (f: Date) => `${f.getFullYear()}-${f.getMonth()}-${f.getDate()}`;
  const dias = new Set(fechas.map((f) => new Date(f)).filter((d) => !Number.isNaN(d.getTime())).map(clave));
  const cursor = new Date(ahora);
  if (!dias.has(clave(cursor))) cursor.setDate(cursor.getDate() - 1);
  let racha = 0;
  while (dias.has(clave(cursor))) {
    racha += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return racha;
}

const RADIO = 34;
const LONGITUD = 2 * Math.PI * RADIO;

function Anillo({porcentaje}: {porcentaje: number}) {
  return (
    <div className="relative size-22 shrink-0" role="img" aria-label={`${porcentaje}% del camino completado`}>
      <svg viewBox="0 0 88 88" className="size-full -rotate-90" aria-hidden="true">
        <circle cx="44" cy="44" r={RADIO} fill="none" className="stroke-surface-highest" strokeWidth="8" />
        <circle
          cx="44"
          cy="44"
          r={RADIO}
          fill="none"
          className="stroke-primary transition-[stroke-dashoffset] duration-700 motion-reduce:transition-none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={LONGITUD}
          strokeDashoffset={LONGITUD * (1 - porcentaje / 100)}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-titulo text-lg font-bold text-on-surface">{porcentaje}%</span>
    </div>
  );
}

function Nodo({estado, pieza}: {estado: Estado | 'proximo'; pieza?: string}) {
  if (estado === 'completado') {
    return (
      <span className="flex size-12 items-center justify-center rounded-full bg-primary text-on-primary" aria-hidden="true">
        <Check size={24} />
      </span>
    );
  }
  if (estado === 'en_curso') {
    return (
      <span className="flex size-12 items-center justify-center rounded-full border-[3px] border-primary bg-surface-lowest shadow-md shadow-primary/30" aria-hidden="true">
        {pieza && <img src={rutaImagenPieza(pieza)} alt="" className="size-8" />}
      </span>
    );
  }
  return (
    <span className={`flex size-12 items-center justify-center rounded-full border-2 border-dashed border-outline-variant text-outline ${estado === 'proximo' ? 'opacity-50' : 'bg-surface-container'}`} aria-hidden="true">
      <Lock size={20} />
    </span>
  );
}

const ETIQUETA: Record<Estado | 'proximo', string> = {
  completado: '¡Listo!',
  en_curso: 'Vas por aquí',
  bloqueado: 'Se abre al terminar el anterior',
  proximo: 'Próximamente',
};

interface Props {
  usuarioId: number | undefined;
  piezasVistas: string[];
  clase: string;
  onIrAPiezas(): void;
}

/** Camino de capítulos del principiante. Lee las partidas reales del jugador para marcar tablero, captura y jaque. */
export default function CaminoProgreso({usuarioId, piezasVistas, clase, onIrAPiezas}: Props) {
  const [partidas, setPartidas] = useState<{fecha: string}[]>([]);
  const [jugadasPorPartida, setJugadasPorPartida] = useState<string[][]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [intento, setIntento] = useState(0);
  const [vistos, setVistos] = useState<string[]>(() => cargarCapitulosVistos(usuarioId));

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    historialPartidasPropio(PARTIDAS_A_REVISAR, 0)
      .then(async (historial: {partidas?: {id: string; fecha: string; cantidad_jugadas: number}[]}) => {
        const jugadas = (historial?.partidas ?? []).filter((p) => p.cantidad_jugadas > 0);
        if (!vigente) return;
        setPartidas(jugadas);
        if (jugadas.length === 0) return;
        // De a pocas partidas, de la más reciente a la más vieja, cortando apenas aparecen una captura y un jaque.
        const acumuladas: string[][] = [];
        for (let desde = 0; desde < jugadas.length; desde += LOTE_DE_PARTIDAS) {
          const detalles = await Promise.allSettled(jugadas.slice(desde, desde + LOTE_DE_PARTIDAS).map((p) => obtenerPartida(p.id)));
          if (!vigente) return;
          detalles.forEach((d) => {
            if (d.status === 'fulfilled') acumuladas.push(d.value?.jugadas ?? []);
          });
          setJugadasPorPartida([...acumuladas]);
          if (desde === 0) setCargando(false);
          if (acumuladas.some(hizoCaptura) && acumuladas.some(dioJaque)) break;
        }
      })
      .catch((err: Error) => vigente && setError(err))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [intento]);

  const marcarVisto = (id: string) =>
    setVistos((actual) => {
      if (actual.includes(id)) return actual;
      const nuevo = [...actual, id];
      guardarCapitulosVistos(usuarioId, nuevo);
      return nuevo;
    });

  const capitulos = useMemo(() => {
    const hechos: Record<string, boolean> = {
      tablero: partidas.length > 0,
      piezas: piezasVistas.length >= 6,
      posicion: vistos.includes('posicion'),
      movimientos: vistos.includes('movimientos'),
      captura: jugadasPorPartida.some(hizoCaptura),
      jaque: jugadasPorPartida.some(dioJaque),
    };
    // Cada capítulo se desbloquea al terminar el anterior: el primero pendiente queda en curso.
    let hayEnCurso = false;
    return CAPITULOS.map((c): Capitulo & {estado: Estado} => {
      if (hechos[c.id]) return {...c, estado: 'completado'};
      if (!hayEnCurso) {
        hayEnCurso = true;
        return {...c, estado: 'en_curso'};
      }
      return {...c, estado: 'bloqueado'};
    });
  }, [partidas, jugadasPorPartida, piezasVistas, vistos]);

  const racha = useMemo(() => rachaDeDias(partidas.map((p) => p.fecha)), [partidas]);

  if (cargando) return <CargandoInline texto="Armando tu camino…" />;
  if (error) return <ErrorReintentar mensaje={`No pudimos cargar tu camino. ${error.message || ''}`} onReintentar={() => setIntento((n) => n + 1)} />;

  const completados = capitulos.filter((c) => c.estado === 'completado').length;
  const porcentaje = Math.round((completados / CAPITULOS.length) * 100);
  const enCurso = capitulos.find((c) => c.estado === 'en_curso');

  const ejecutar = (accion: Accion) => (accion.tipo === 'piezas' ? onIrAPiezas() : irA(accion.ruta));

  return (
    <>
      <div className="flex items-center gap-4 rounded-2xl bg-primary-container p-4">
        <Anillo porcentaje={porcentaje} />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="flex w-fit items-center gap-1 rounded-full bg-tertiary-container px-3 py-1 text-xs font-semibold text-on-tertiary-container">
            <Flame size={14} aria-hidden="true" />
            {racha > 0 ? (racha === 1 ? '1 día seguido' : `${racha} días seguidos`) : 'Juega hoy para arrancar una racha'}
          </span>
          <p className="font-titulo text-base font-bold text-on-primary-container">
            {completados} de {CAPITULOS.length} capítulos listos
          </p>
          <p className="text-sm text-on-primary-container">
            {enCurso ? <>Siguiente paso: <strong>{enCurso.titulo}</strong></> : 'Terminaste los capítulos disponibles. Pronto llegan más.'}
          </p>
        </div>
      </div>

      {enCurso && (
        <section aria-label="Paso actual" className="flex flex-col gap-2 rounded-2xl border border-primary bg-surface-lowest p-4">
          <span className="text-xs font-bold uppercase tracking-wide text-primary">Paso actual · {enCurso.titulo}</span>
          <p className={`${clase} text-on-surface`}>{enCurso.descripcion}</p>
          <div className="flex flex-col gap-2">
            {enCurso.accion && <BotonPrimario onClick={() => ejecutar(enCurso.accion as Accion)}>{enCurso.accion.texto}</BotonPrimario>}
            {enCurso.marcable && (
              <BotonPrimario variante="secundario" onClick={() => marcarVisto(enCurso.id)}>
                ¡Ya la vi!
              </BotonPrimario>
            )}
          </div>
        </section>
      )}

      <ol className="flex flex-col" aria-label="Capítulos del camino">
        {[...capitulos, ...PROXIMOS.map((titulo) => ({id: titulo, titulo, pieza: undefined, estado: 'proximo' as const}))].map((fila, i, todas) => (
          <li key={fila.id} className="relative flex items-center gap-3 pb-5 last:pb-0">
            {i < todas.length - 1 && (
              <span
                aria-hidden="true"
                className={`absolute left-6 top-12 bottom-0 -ml-px w-0.5 ${fila.estado === 'completado' ? 'bg-primary' : 'bg-outline-variant'}`}
              />
            )}
            <Nodo estado={fila.estado} pieza={fila.pieza} />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-on-surface">{fila.titulo}</p>
              <p className={`text-xs ${fila.estado === 'completado' ? 'font-semibold text-primary' : fila.estado === 'en_curso' ? 'font-semibold text-on-surface' : 'text-on-surface-variant'}`}>
                Capítulo {i + 1} · {ETIQUETA[fila.estado]}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}
