import {useState, type FormEvent, type ReactNode} from 'react';
import {Eye, EyeOff} from 'lucide-react';
import BotonPrimario from '../../componentes/BotonPrimario';
import GlassCard from '../../componentes/GlassCard';
import {useSesion} from '../../estado/SesionContext';

const MIN_NOMBRE = 2;
const MIN_PASSWORD = 6;
const CLASES_CAMPO =
  'w-full rounded-boton border border-outline-variant bg-surface-lowest px-4 py-3 text-base text-on-surface placeholder:text-outline';

/** Convierte el error del backend en un mensaje claro para el jugador. */
function mensajeDeError(error: unknown): string {
  const texto = error instanceof Error ? error.message : '';
  if (/solo para rol|tiene rol/i.test(texto)) {
    return 'Esta cuenta es de facilitador. Esta app es solo para jugadores: entrá con una cuenta de jugador o creá una nueva.';
  }
  if (/credenciales/i.test(texto)) return 'Correo o contraseña incorrectos.';
  if (/ya registrado/i.test(texto)) return 'Ese correo ya tiene una cuenta. Probá iniciar sesión.';
  if (/failed to fetch|networkerror|load failed/i.test(texto)) return 'No se pudo conectar con el servidor. Revisá que el backend esté encendido.';
  return texto || 'No se pudo completar la acción. Intentá de nuevo.';
}

interface CampoProps {
  id: string;
  etiqueta: string;
  type?: string;
  valor: string;
  onCambio: (valor: string) => void;
  autoComplete?: string;
  derecha?: ReactNode;
}

function Campo({id, etiqueta, type = 'text', valor, onCambio, autoComplete, derecha}: CampoProps) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-semibold text-on-surface-variant">
        {etiqueta}
      </label>
      <div className="relative">
        <input
          id={id}
          type={type}
          value={valor}
          onChange={(e) => onCambio(e.target.value)}
          autoComplete={autoComplete}
          required
          className={CLASES_CAMPO}
        />
        {derecha}
      </div>
    </div>
  );
}

export default function Login() {
  const {login, registrar} = useSesion();
  const [esLogin, setEsLogin] = useState(true);
  const [nombre, setNombre] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function alternarModo() {
    setError(null);
    setEsLogin((valor) => !valor);
  }

  /** Validación previa al envío: evita que un 422 del backend llegue como texto ilegible. */
  function validar(): string | null {
    if (esLogin) return null;
    if (nombre.trim().length < MIN_NOMBRE) return `El nombre debe tener al menos ${MIN_NOMBRE} caracteres.`;
    if (password.length < MIN_PASSWORD) return `La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`;
    if (password !== confirmacion) return 'Las contraseñas no coinciden.';
    return null;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const problema = validar();
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    setCargando(true);
    try {
      if (esLogin) await login(email, password);
      else await registrar(email, nombre, password);
      // La guardia de sesión de App.tsx redirige a /inicio al detectar el usuario.
    } catch (err) {
      setError(mensajeDeError(err));
      setCargando(false);
    }
  }

  const tipoPassword = verPassword ? 'text' : 'password';
  return (
    <section className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-linear-to-b from-surface-lowest via-surface to-primary-container px-4 py-8">
      <img src="/logo.png" alt="ChessIA" className="h-auto w-48" />
      <GlassCard className="w-full p-6">
        <form onSubmit={enviar} className="flex flex-col gap-4">
          <h1 className="text-center font-titulo text-2xl font-bold text-on-surface">{esLogin ? 'Iniciar sesión' : 'Crear cuenta'}</h1>
          {!esLogin && <Campo id="nombre" etiqueta="Nombre" valor={nombre} onCambio={setNombre} autoComplete="name" />}
          <Campo id="email" etiqueta="Correo electrónico" type="email" valor={email} onCambio={setEmail} autoComplete="email" />
          <Campo
            id="password"
            etiqueta="Contraseña"
            type={tipoPassword}
            valor={password}
            onCambio={setPassword}
            autoComplete={esLogin ? 'current-password' : 'new-password'}
            derecha={
              <button
                type="button"
                onClick={() => setVerPassword((v) => !v)}
                aria-label={verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                className="absolute inset-y-0 right-0 flex w-12 items-center justify-center rounded-boton text-on-surface-variant"
              >
                {verPassword ? <EyeOff size={20} aria-hidden="true" /> : <Eye size={20} aria-hidden="true" />}
              </button>
            }
          />
          {!esLogin && (
            <Campo
              id="confirmacion"
              etiqueta="Confirmar contraseña"
              type={tipoPassword}
              valor={confirmacion}
              onCambio={setConfirmacion}
              autoComplete="new-password"
            />
          )}
          {error && (
            <p role="alert" className="rounded-boton bg-error-container px-4 py-3 text-sm font-medium text-on-error-container">
              {error}
            </p>
          )}
          <BotonPrimario type="submit" cargando={cargando} textoCargando={esLogin ? 'Entrando…' : 'Creando cuenta…'}>
            {esLogin ? 'Entrar' : 'Registrarse'}
          </BotonPrimario>
          <p className="text-center text-sm text-on-surface-variant">
            {esLogin ? '¿No tenés cuenta?' : '¿Ya tenés cuenta?'}{' '}
            <button type="button" onClick={alternarModo} className="rounded font-semibold text-primary underline-offset-2 hover:underline">
              {esLogin ? 'Registrate' : 'Iniciá sesión'}
            </button>
          </p>
        </form>
      </GlassCard>
    </section>
  );
}
