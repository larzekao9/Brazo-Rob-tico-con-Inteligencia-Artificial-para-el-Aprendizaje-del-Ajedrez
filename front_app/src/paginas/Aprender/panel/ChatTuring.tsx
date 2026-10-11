import {Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode} from 'react';
import {Brain, Mic, MicOff, RotateCcw, Send, Volume2, VolumeX} from 'lucide-react';
import {borrarHistorialTutor, enviarMensajeTutor, obtenerHistorialTutor} from '../../../api/backend';
import ErrorReintentar from '../../../componentes/ErrorReintentar';
import type {Usuario} from '../../../estado/SesionContext';
import {CargandoInline, Vacio} from './ui';
import type {Narracion} from './voz';

interface Mensaje {
  id: number;
  rol: 'user' | 'assistant';
  contenido: string;
}

let contadorMensajes = 0;
/** Id de React para cada burbuja: nunca se manda al backend, solo sirve de `key`. */
const nuevoId = () => (contadorMensajes += 1);

/** Negrita, cursiva y código en línea de las respuestas de Turing; el resto se muestra como texto. */
function lineaConMarkdown(linea: string): ReactNode[] {
  return linea.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).map((parte, i) => {
    if (parte.startsWith('**') && parte.endsWith('**') && parte.length >= 4) return <strong key={i}>{parte.slice(2, -2)}</strong>;
    if (parte.startsWith('*') && parte.endsWith('*') && parte.length >= 2) return <em key={i}>{parte.slice(1, -1)}</em>;
    if (parte.startsWith('`') && parte.endsWith('`') && parte.length >= 2) return <code key={i} className="rounded bg-surface-container px-1 py-0.5 text-xs">{parte.slice(1, -1)}</code>;
    return parte;
  });
}

function ContenidoTutor({texto}: {texto: string}) {
  return (
    <div className="flex flex-col gap-2 text-sm leading-relaxed">
      {texto.split(/\n{2,}/).map((parrafo, i) => (
        <p key={i}>
          {parrafo.split('\n').map((linea, j) => (
            <Fragment key={j}>
              {j > 0 && <br />}
              {lineaConMarkdown(linea)}
            </Fragment>
          ))}
        </p>
      ))}
    </div>
  );
}

/** 404/405 = el servidor todavía no tiene el tutor. */
function mensajeHistorial(error: Error & {status?: number}): string {
  if (error.status === 404 || error.status === 405) return 'El tutor Turing todavía no está disponible en este servidor. Prueba de nuevo en un rato.';
  return error.message || 'No se pudo cargar tu conversación con Turing.';
}

/** 503 = tutor caído o sin API key: es el caso esperado, no un fallo de la app. */
function mensajeEnvio(error: Error & {status?: number}): string {
  if (error.status === 503) return 'Turing no está disponible en este momento, prueba de nuevo en un rato.';
  return error.message || 'No se pudo mandar tu mensaje. Prueba de nuevo en un rato.';
}

interface Reconocimiento {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((evento: {results: ArrayLike<ArrayLike<{transcript: string}>>}) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start(): void;
  abort(): void;
}

function crearReconocimiento(): Reconocimiento | null {
  const ctor = (window as unknown as {SpeechRecognition?: new () => Reconocimiento; webkitSpeechRecognition?: new () => Reconocimiento}).SpeechRecognition
    ?? (window as unknown as {webkitSpeechRecognition?: new () => Reconocimiento}).webkitSpeechRecognition;
  return ctor ? new ctor() : null;
}

const SUGERENCIAS = ['¿Cómo se mueve el caballo?', '¿Cómo se enroca?', '¿Qué es un jaque mate?'];

interface Props {
  usuario: Usuario | null;
  voz: Narracion;
  /** true = ocupa toda la altura disponible (pantalla del tutor); false = alto acotado dentro del panel. */
  lleno?: boolean;
}

/** Chat con el tutor Turing: historial, envío, reinicio de la conversación, lectura en voz alta y dictado. */
export default function ChatTuring({usuario, voz, lleno = false}: Props) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [cargando, setCargando] = useState(true);
  const [errorHistorial, setErrorHistorial] = useState<Error | null>(null);
  const [intento, setIntento] = useState(0);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState<Error | null>(null);
  const [borrando, setBorrando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [escuchando, setEscuchando] = useState(false);
  const [hayDictado, setHayDictado] = useState(false);
  const finRef = useRef<HTMLLIElement>(null);
  const reconocimientoRef = useRef<Reconocimiento | null>(null);
  const nombre = usuario?.nombre?.trim().split(/\s+/)[0] || null;

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setErrorHistorial(null);
    obtenerHistorialTutor(50)
      .then((datos: {turnos?: {rol: string; contenido: string}[]}) => {
        if (!vigente) return;
        setMensajes((datos?.turnos ?? []).map((t) => ({id: nuevoId(), rol: t.rol === 'user' ? 'user' : 'assistant', contenido: t.contenido})));
      })
      .catch((err: Error) => vigente && setErrorHistorial(err))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [intento]);

  useEffect(() => {
    finRef.current?.scrollIntoView({behavior: 'smooth', block: 'end'});
  }, [mensajes.length, enviando]);

  useEffect(() => {
    const reconocimiento = crearReconocimiento();
    if (reconocimiento) {
      reconocimiento.lang = 'es-ES';
      reconocimiento.continuous = false;
      reconocimiento.interimResults = false;
      reconocimiento.onresult = (evento) => {
        setTexto(evento.results[0][0].transcript);
        setEscuchando(false);
      };
      reconocimiento.onerror = () => setEscuchando(false);
      reconocimiento.onend = () => setEscuchando(false);
    }
    reconocimientoRef.current = reconocimiento;
    setHayDictado(reconocimiento !== null);
    return () => reconocimiento?.abort();
  }, []);

  const alternarDictado = () => {
    if (escuchando) {
      reconocimientoRef.current?.abort();
      setEscuchando(false);
    } else {
      reconocimientoRef.current?.start();
      setEscuchando(true);
    }
  };

  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    const mensaje = texto.trim();
    if (!mensaje || enviando || cargando) return;
    // El mensaje se agrega antes de la respuesta; si el envío falla se queda en la lista y el aviso se muestra aparte.
    setMensajes((actual) => [...actual, {id: nuevoId(), rol: 'user', contenido: mensaje}]);
    setTexto('');
    setErrorEnvio(null);
    setEnviando(true);
    enviarMensajeTutor(mensaje)
      .then((r: {respuesta: string}) => setMensajes((actual) => [...actual, {id: nuevoId(), rol: 'assistant', contenido: r.respuesta}]))
      .catch((err: Error) => setErrorEnvio(err))
      .finally(() => setEnviando(false));
  };

  const reiniciar = () => {
    setBorrando(true);
    setErrorEnvio(null);
    borrarHistorialTutor()
      .then(() => {
        setMensajes([]);
        setConfirmando(false);
      })
      .catch((err: Error) => setErrorEnvio(err))
      .finally(() => setBorrando(false));
  };

  return (
    <div className={`flex flex-col gap-3 ${lleno ? 'min-h-0 flex-1' : ''}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-on-surface-variant">Pregúntale a Turing sobre reglas de ajedrez o tu última partida.</p>
        {mensajes.length > 0 &&
          (confirmando ? (
            <span className="flex items-center gap-2 text-xs">
              <span className="text-on-surface-variant">¿Borrar la conversación?</span>
              <button type="button" onClick={reiniciar} disabled={borrando} aria-busy={borrando} className="min-h-9 rounded-full bg-error px-3 font-semibold text-on-error disabled:opacity-50">
                {borrando ? 'Borrando…' : 'Sí, borrar'}
              </button>
              <button type="button" onClick={() => setConfirmando(false)} disabled={borrando} className="min-h-9 rounded-full bg-surface-container px-3 font-semibold text-on-surface disabled:opacity-50">
                No
              </button>
            </span>
          ) : (
            <button type="button" onClick={() => setConfirmando(true)} className="flex min-h-9 items-center gap-1 rounded-full bg-surface-container px-3 text-xs font-semibold text-on-surface-variant">
              <RotateCcw size={14} aria-hidden="true" />
              Reiniciar conversación
            </button>
          ))}
      </div>

      {cargando && <CargandoInline texto="Cargando tu conversación con Turing…" />}
      {!cargando && errorHistorial && <ErrorReintentar mensaje={mensajeHistorial(errorHistorial)} onReintentar={() => setIntento((n) => n + 1)} />}

      {!cargando && !errorHistorial && mensajes.length === 0 && (
        <>
          <Vacio>
            Todavía no le preguntaste nada a Turing{nombre ? `, ${nombre}` : ''}. Escribe una pregunta abajo, por ejemplo “¿cómo se mueve el caballo?”.
          </Vacio>
          <div className="flex flex-wrap gap-2">
            {SUGERENCIAS.map((s) => (
              <button key={s} type="button" onClick={() => setTexto(s)} className="min-h-9 rounded-full bg-surface-container px-3 text-xs font-semibold text-on-surface-variant">
                {s}
              </button>
            ))}
          </div>
        </>
      )}

      {mensajes.length > 0 && (
        <ul aria-label="Conversación con Turing" className={`flex flex-col gap-2 overflow-y-auto rounded-2xl bg-surface-low p-2 ${lleno ? 'min-h-0 flex-1' : 'max-h-96'}`}>
          {mensajes.map((m) => (
            <li key={m.id} aria-label={m.rol === 'user' ? 'Tu mensaje' : 'Respuesta de Turing'} className={`flex ${m.rol === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-[85%] flex-col gap-1 rounded-2xl px-3 py-2 ${m.rol === 'user' ? 'rounded-br-sm bg-primary text-on-primary' : 'rounded-bl-sm bg-surface-lowest text-on-surface'}`}>
                {m.rol === 'assistant' && (
                  <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-primary">
                    <Brain size={12} aria-hidden="true" />
                    Turing
                  </span>
                )}
                {m.rol === 'user' ? <p className="whitespace-pre-wrap text-sm">{m.contenido}</p> : <ContenidoTutor texto={m.contenido} />}
                {m.rol === 'assistant' && voz.disponible && (
                  <button
                    type="button"
                    onClick={() => (voz.narrando ? voz.detener() : voz.narrar(m.contenido))}
                    aria-label={voz.narrando ? 'Detener la lectura en voz alta' : 'Escuchar esta respuesta de Turing'}
                    className="flex min-h-8 w-fit items-center gap-1 rounded-full bg-surface-container px-3 text-xs font-semibold text-on-surface-variant"
                  >
                    {voz.narrando ? <VolumeX size={12} aria-hidden="true" /> : <Volume2 size={12} aria-hidden="true" />}
                    {voz.narrando ? 'Detener' : 'Escuchar'}
                  </button>
                )}
              </div>
            </li>
          ))}
          <li ref={finRef} aria-hidden="true" />
        </ul>
      )}

      {enviando && <CargandoInline texto="Turing está pensando…" />}
      {!enviando && errorEnvio && <ErrorReintentar mensaje={mensajeEnvio(errorEnvio)} />}

      <form onSubmit={enviar} className="flex items-center gap-2">
        {hayDictado && (
          <button
            type="button"
            onClick={alternarDictado}
            disabled={enviando}
            aria-label={escuchando ? 'Dejar de escuchar' : 'Dictar mensaje'}
            aria-pressed={escuchando}
            className={`flex size-11 shrink-0 items-center justify-center rounded-full disabled:opacity-50 ${escuchando ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant'}`}
          >
            {escuchando ? <MicOff size={18} aria-hidden="true" /> : <Mic size={18} aria-hidden="true" />}
          </button>
        )}
        <input
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          disabled={enviando || cargando}
          maxLength={2000}
          placeholder="Escribe tu pregunta para Turing…"
          aria-label="Mensaje para Turing"
          className="min-h-11 min-w-0 flex-1 rounded-full bg-surface-container px-4 text-sm text-on-surface placeholder:text-on-surface-variant disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={enviando || cargando || !texto.trim()}
          aria-label="Enviar mensaje"
          className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-on-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send size={18} aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}
