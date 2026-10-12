import {useState, type FormEvent} from 'react';
import {Check, ChevronLeft, LogIn, Plus} from 'lucide-react';
import {crearSala, unirseASala} from '../../api/sala';
import BotonPrimario from '../../componentes/BotonPrimario';
import GlassCard from '../../componentes/GlassCard';
import {irA} from '../../router';
import {normalizarCodigo} from '../Sala/enlace';
import {mensajeDeError} from '../Sala/salaUtil';
import TarjetaSalaActiva from '../Sala/TarjetaSalaActiva';
import type {ErrorApi, SalaEstado} from '../Sala/tipos';

type ColorElegido = 'aleatorio' | 'blancas' | 'negras';

const COLORES: {valor: ColorElegido; etiqueta: string}[] = [
  {valor: 'aleatorio', etiqueta: 'Al azar'},
  {valor: 'blancas', etiqueta: 'Blancas'},
  {valor: 'negras', etiqueta: 'Negras'},
];

/** /amigo: crear una sala para jugar con un amigo o unirse a una con su código. */
export default function Amigo() {
  const [color, setColor] = useState<ColorElegido>('aleatorio');
  const [codigo, setCodigo] = useState('');
  const [creando, setCreando] = useState(false);
  const [uniendo, setUniendo] = useState(false);
  const [errorCrear, setErrorCrear] = useState<string | null>(null);
  const [errorUnirse, setErrorUnirse] = useState<string | null>(null);

  async function crear() {
    setCreando(true);
    setErrorCrear(null);
    try {
      const sala = (await crearSala(color)) as SalaEstado;
      irA('/sala/:codigo', {codigo: sala.codigo});
    } catch (err) {
      setErrorCrear(mensajeDeError(err, 'No se pudo crear la sala.'));
      setCreando(false);
    }
  }

  async function unirse(evento: FormEvent) {
    evento.preventDefault();
    const limpio = normalizarCodigo(codigo);
    if (!limpio) {
      setErrorUnirse('Escribe el código de la sala.');
      return;
    }
    setUniendo(true);
    setErrorUnirse(null);
    try {
      await unirseASala(limpio);
      irA('/sala/:codigo', {codigo: limpio});
    } catch (err) {
      setErrorUnirse((err as ErrorApi).status === 404 ? 'No existe esa sala.' : mensajeDeError(err, 'No se pudo unir a la sala.'));
      setUniendo(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 p-4 pb-8">
      <header className="flex items-center gap-2">
        <button type="button" onClick={() => irA('/inicio')} aria-label="Volver al inicio" className="flex size-11 items-center justify-center rounded-full text-on-surface hover:bg-surface-container">
          <ChevronLeft size={24} aria-hidden="true" />
        </button>
        <div>
          <h1 className="font-titulo text-xl font-bold text-on-surface">Jugar con un amigo</h1>
          <p className="text-xs text-on-surface-variant">Crea una sala y comparte el enlace, o entra con un código.</p>
        </div>
      </header>

      <TarjetaSalaActiva />

      <GlassCard className="flex flex-col gap-4">
        <h2 className="font-titulo text-lg font-bold text-on-surface">Crear una sala</h2>
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-semibold text-on-surface-variant">Tu color</legend>
          <div role="radiogroup" aria-label="Tu color" className="grid grid-cols-3 gap-2">
            {COLORES.map(({valor, etiqueta}) => {
              const elegido = color === valor;
              return (
                <button
                  key={valor}
                  type="button"
                  role="radio"
                  aria-checked={elegido}
                  onClick={() => setColor(valor)}
                  className={`flex min-h-12 items-center justify-center gap-1 rounded-boton border px-2 text-sm font-semibold ${
                    elegido ? 'border-primary bg-primary-container text-on-primary-container ring-2 ring-primary' : 'border-outline-variant bg-surface-lowest text-on-surface'
                  }`}
                >
                  {elegido && <Check size={16} aria-hidden="true" />}
                  {etiqueta}
                </button>
              );
            })}
          </div>
        </fieldset>
        {errorCrear && (
          <p role="alert" className="rounded-boton bg-error-container px-4 py-3 text-sm font-medium text-on-error-container">
            {errorCrear}
          </p>
        )}
        <BotonPrimario cargando={creando} textoCargando="Creando sala…" onClick={() => void crear()}>
          <Plus size={18} aria-hidden="true" /> Crear sala
        </BotonPrimario>
      </GlassCard>

      <GlassCard>
        <form onSubmit={unirse} className="flex flex-col gap-4">
          <h2 className="font-titulo text-lg font-bold text-on-surface">Unirme con código</h2>
          <div>
            <label htmlFor="codigo-sala" className="mb-1 block text-sm font-semibold text-on-surface-variant">
              Código de la sala
            </label>
            <input
              id="codigo-sala"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              maxLength={12}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              placeholder="K7M2QX"
              className="w-full rounded-boton border border-outline-variant bg-surface-lowest px-4 py-3 text-center font-titulo text-xl uppercase tracking-widest text-on-surface placeholder:text-outline"
            />
          </div>
          {errorUnirse && (
            <p role="alert" className="rounded-boton bg-error-container px-4 py-3 text-sm font-medium text-on-error-container">
              {errorUnirse}
            </p>
          )}
          <BotonPrimario type="submit" variante="secundario" cargando={uniendo} textoCargando="Entrando…">
            <LogIn size={18} aria-hidden="true" /> Unirme
          </BotonPrimario>
        </form>
      </GlassCard>
    </section>
  );
}
