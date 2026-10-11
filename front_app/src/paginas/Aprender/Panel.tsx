import {useCallback, useEffect, useMemo, useState, type ReactNode} from 'react';
import {Award, BarChart3, BookOpen, Brain, ClipboardList, Lock, Map as MapIcon, MessageCircle, Puzzle, Route, Type, Volume2, VolumeX} from 'lucide-react';
import GlassCard from '../../componentes/GlassCard';
import {useSesion} from '../../estado/SesionContext';
import {irA} from '../../router';
import CaminoProgreso from './panel/CaminoProgreso';
import ChatTuring from './panel/ChatTuring';
import Estadisticas from './panel/Estadisticas';
import GaleriaPiezas from './panel/GaleriaPiezas';
import LeccionesGuiadas from './panel/LeccionesGuiadas';
import Logros, {calcularInsignias} from './panel/Logros';
import Proximamente from './panel/Proximamente';
import Repaso, {tarjetasDeRepaso, textoNarrableDeJugada} from './panel/Repaso';
import ResumenTutor from './panel/ResumenTutor';
import Seccion from './panel/Seccion';
import TuNivel from './panel/TuNivel';
import {claseTexto} from './panel/ui';
import {useUltimaPartida} from './panel/useUltimaPartida';
import {cargarLecturaFacil, cargarPiezasVistas, guardarLecturaFacil, guardarPiezasVistas} from './panel/prefs';
import {useNarracion} from './panel/voz';

type IdSeccion = 'nivel' | 'camino' | 'lecciones' | 'repaso' | 'piezas' | 'resumen' | 'turing' | 'estadisticas' | 'logros' | 'proximamente';

/** Secciones que usan el análisis completo de la última partida (lo más pesado: se pide solo cuando alguna está abierta). */
const CON_ANALISIS: IdSeccion[] = ['repaso', 'resumen', 'logros'];

const ICONO: Record<IdSeccion, ReactNode> = {
  nivel: <Award size={18} />,
  camino: <Route size={18} />,
  lecciones: <BookOpen size={18} />,
  repaso: <ClipboardList size={18} />,
  piezas: <Puzzle size={18} />,
  resumen: <Brain size={18} />,
  turing: <MessageCircle size={18} />,
  estadisticas: <BarChart3 size={18} />,
  logros: <MapIcon size={18} />,
  proximamente: <Lock size={18} />,
};

const TITULO: Record<IdSeccion, string> = {
  nivel: 'Tu nivel',
  camino: 'Tu camino',
  lecciones: 'Lecciones guiadas',
  repaso: 'Repaso de tu partida',
  piezas: 'Aprende cada pieza',
  resumen: 'Resumen del tutor',
  turing: 'Pregúntale a Turing',
  estadisticas: 'Tus estadísticas',
  logros: 'Tus logros',
  proximamente: 'Próximamente',
};

/**
 * Panel de Aprender (RF20): nivel y camino de progreso, repaso de la última partida adaptado al nivel, galería de
 * piezas, tutor Turing, estadísticas, logros y lo que viene. Cada sección pide sus datos al abrirse, así que si una
 * falla las demás siguen funcionando.
 */
export default function Panel() {
  const {usuario} = useSesion();
  const idUsuario = usuario?.id;
  const rango = usuario?.rango_estimado || 'Intermedio';
  // El camino de capítulos es para quien aprende las bases: principiantes y quienes todavía no se midieron.
  const muestraCamino = !usuario?.rango_estimado || usuario.rango_estimado === 'Principiante';
  const nombre = usuario?.nombre?.trim().split(/\s+/)[0] || 'jugador';

  const [abiertas, setAbiertas] = useState<Set<IdSeccion>>(() => new Set<IdSeccion>(muestraCamino ? ['nivel', 'camino'] : ['nivel', 'repaso']));
  const [piezasVistas, setPiezasVistas] = useState<string[]>(() => cargarPiezasVistas(idUsuario));
  const [lecturaFacil, setLecturaFacil] = useState(() => cargarLecturaFacil(idUsuario));
  const [narrarAlCargar, setNarrarAlCargar] = useState(false);
  const voz = useNarracion();
  const clase = claseTexto(lecturaFacil);

  const necesitaAnalisis = CON_ANALISIS.some((id) => abiertas.has(id));
  const partida = useUltimaPartida(rango, necesitaAnalisis);

  const alternar = useCallback((id: IdSeccion) => {
    setAbiertas((actual) => {
      const nuevo = new Set(actual);
      if (!nuevo.delete(id)) nuevo.add(id);
      return nuevo;
    });
  }, []);

  const abrirYMostrar = useCallback((id: IdSeccion) => {
    setAbiertas((actual) => new Set(actual).add(id));
    requestAnimationFrame(() => document.getElementById(`seccion-${id}`)?.scrollIntoView({behavior: 'smooth', block: 'start'}));
  }, []);

  const verPieza = (tipo: string) =>
    setPiezasVistas((actual) => {
      if (actual.includes(tipo)) return actual;
      const nuevo = [...actual, tipo];
      guardarPiezasVistas(idUsuario, nuevo);
      return nuevo;
    });

  const alternarLecturaFacil = () =>
    setLecturaFacil((actual) => {
      guardarLecturaFacil(idUsuario, !actual);
      return !actual;
    });

  const textoRepaso = useMemo(() => tarjetasDeRepaso(partida.analisis?.jugadas).map(textoNarrableDeJugada).join(' '), [partida.analisis]);

  // "Escuchar el repaso": abre la sección (que dispara el análisis) y lee apenas hay texto.
  useEffect(() => {
    if (narrarAlCargar && textoRepaso) {
      setNarrarAlCargar(false);
      voz.narrar(textoRepaso);
    }
  }, [narrarAlCargar, textoRepaso, voz]);

  const escucharRepaso = () => {
    if (voz.narrando) return voz.detener();
    abrirYMostrar('repaso');
    if (textoRepaso) voz.narrar(textoRepaso);
    else setNarrarAlCargar(true);
  };
  const sinPartidas = !partida.cargandoHistorial && !partida.ultima;

  const insignias = calcularInsignias({
    totalPartidas: partida.totalPartidas,
    piezasVistas: piezasVistas.length,
    repasada: partida.analisis !== null,
    mostrarPiezas: muestraCamino,
  });

  const seccion = (id: IdSeccion, contenido: ReactNode) => (
    <Seccion id={id} titulo={TITULO[id]} icono={ICONO[id]} abierta={abiertas.has(id)} onAlternar={() => alternar(id)}>
      {contenido}
    </Seccion>
  );

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="sticky top-0 z-10 border-b border-outline-variant bg-surface/80 px-4 py-3 backdrop-blur-md">
        <p className="text-xs font-medium tracking-wide text-primary">APRENDER</p>
        <h1 className="font-titulo text-xl font-bold text-on-surface">Panel de aprendizaje</h1>
      </header>

      <div className="flex flex-col gap-4 p-4">
        <GlassCard className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary-container text-primary" aria-hidden="true">
              <Brain size={26} />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-wide text-primary">Turing · tu tutor</p>
              <p className="font-titulo text-lg font-bold text-on-surface">Hola {nombre}, repasemos tu ajedrez</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={alternarLecturaFacil}
              aria-pressed={lecturaFacil}
              className={`flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-semibold ${lecturaFacil ? 'border-primary bg-primary-container text-on-primary-container' : 'border-outline-variant bg-surface-lowest text-on-surface'}`}
            >
              <Type size={16} aria-hidden="true" />
              Lectura fácil
            </button>
            {voz.disponible && (
              <button
                type="button"
                onClick={escucharRepaso}
                disabled={sinPartidas}
                className="flex min-h-11 items-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-on-primary disabled:opacity-50"
              >
                {voz.narrando ? <VolumeX size={16} aria-hidden="true" /> : <Volume2 size={16} aria-hidden="true" />}
                {voz.narrando ? 'Detener' : 'Escuchar el repaso'}
              </button>
            )}
          </div>
          {!voz.disponible && <p className="text-xs text-on-surface-variant">La narración por voz no está disponible en este navegador; el resto del panel funciona igual.</p>}
        </GlassCard>

        {seccion('nivel', <TuNivel usuario={usuario} clase={clase} />)}
        {muestraCamino && seccion('camino', <CaminoProgreso usuarioId={idUsuario} piezasVistas={piezasVistas} clase={clase} onIrAPiezas={() => abrirYMostrar('piezas')} />)}
        {seccion('lecciones', <LeccionesGuiadas />)}
        {seccion('repaso', <Repaso datos={partida} clase={clase} voz={voz} />)}
        {seccion('resumen', <ResumenTutor datos={partida} clase={clase} />)}
        {seccion('piezas', <GaleriaPiezas vistas={piezasVistas} onVer={verPieza} clase={clase} />)}
        {seccion(
          'turing',
          <>
            <ChatTuring usuario={usuario} voz={voz} />
            <button type="button" onClick={() => irA('/aprender/tutor')} className="min-h-11 rounded-full bg-surface-container px-4 text-sm font-semibold text-primary">
              Abrir el chat en pantalla completa
            </button>
          </>,
        )}
        {seccion('estadisticas', <Estadisticas />)}
        {seccion('logros', <Logros insignias={insignias} cargando={partida.analizando} />)}
        {seccion('proximamente', <Proximamente />)}
      </div>
    </div>
  );
}
