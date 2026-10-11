import {useCallback, useEffect, useState, type ReactNode} from 'react';
import {BarChart3, Flame, Play, Quote, Radio, Target, Trophy} from 'lucide-react';
import {obtenerDemostracionActiva, obtenerNivelJugador} from '../../api/backend';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import GlassCard from '../../componentes/GlassCard';
import ProgresoBarra from '../../componentes/ProgresoBarra';
import RadarHabilidades from '../../componentes/RadarHabilidades';
import {precisionAPorcentaje} from '../../dominio/nivelJugador';
import {useSesion, type Usuario} from '../../estado/SesionContext';
import {irA} from '../../router';
import PartidaPendiente from './PartidaPendiente';
import {ejesDeRadar, fraseDelDia, textoPorcentaje, type NivelJugador} from './datosInicio';

function Avatar({usuario}: {usuario: Usuario}) {
  if (usuario.avatar_url) {
    return <img src={usuario.avatar_url} alt="" className="size-14 rounded-full object-cover" />;
  }
  return (
    <span aria-hidden="true" className="flex size-14 items-center justify-center rounded-full bg-surface-highest font-titulo text-xl font-bold text-primary">
      {usuario.nombre.charAt(0).toUpperCase()}
    </span>
  );
}

function Estadistica({icono, etiqueta, valor}: {icono: ReactNode; etiqueta: string; valor: string}) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1 px-1 text-center">
      {icono}
      <span className="text-xs text-on-surface-variant">{etiqueta}</span>
      <span className="font-titulo text-2xl font-bold text-on-surface">{valor}</span>
    </div>
  );
}

function ProgresoNivel({nivel, usuario}: {nivel: NivelJugador | null; usuario: Usuario}) {
  const actual = nivel?.nivel_estimado ?? usuario.nivel_estimado;
  const progreso = nivel?.progreso_siguiente_nivel;
  const objetivo = nivel?.precision_siguiente_nivel;
  return (
    <div className="flex flex-col gap-2 rounded-tarjeta bg-surface-low p-4">
      <h3 className="font-titulo text-base font-bold text-on-surface">Tu progreso</h3>
      {actual === null || actual === undefined ? (
        <p className="text-sm text-on-surface-variant">Juega tu primera partida para medir tu nivel.</p>
      ) : (
        <>
          <p className="text-xs text-on-surface-variant">Siguiente nivel</p>
          <p className="font-titulo text-lg font-bold text-on-surface">Nivel {actual + 1}</p>
          {typeof progreso === 'number' ? (
            <>
              <ProgresoBarra valor={progreso * 100} etiqueta="Avance hacia el siguiente nivel" />
              {typeof objetivo === 'number' && (
                <p className="text-right text-xs text-on-surface-variant">
                  {textoPorcentaje(precisionAPorcentaje(nivel?.precision_promedio))} / {textoPorcentaje(precisionAPorcentaje(objetivo))} de precisión
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-on-surface-variant">—</p>
          )}
        </>
      )}
    </div>
  );
}

export default function Inicio() {
  const {usuario, estadisticas, cargarEstadisticas, recargarUsuario} = useSesion();
  const [nivel, setNivel] = useState<NivelJugador | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hayDemostracion, setHayDemostracion] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      // El progreso de nivel es secundario: si /auth/nivel falla se muestra "—" y el resto sigue.
      const pedidoNivel = obtenerNivelJugador()
        .then((datos: NivelJugador) => setNivel(datos))
        .catch(() => setNivel(null));
      await Promise.all([pedidoNivel, cargarEstadisticas(), recargarUsuario()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron cargar tus datos.');
    } finally {
      setCargando(false);
    }
  }, [cargarEstadisticas, recargarUsuario]);

  useEffect(() => {
    void cargar();
    // El banner es opcional: si falla la consulta simplemente no se muestra.
    obtenerDemostracionActiva()
      .then((partida: unknown) => setHayDemostracion(partida !== null))
      .catch(() => setHayDemostracion(false));
  }, [cargar]);

  if (!usuario) return null;
  const rango = nivel?.rango_estimado ?? usuario.rango_estimado;
  const sinDatos = estadisticas === null;

  return (
    <section className="flex flex-col gap-4 p-4">
      <header className="flex items-center gap-3">
        <Avatar usuario={usuario} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-titulo text-xl font-bold text-on-surface">Hola, {usuario.nombre.split(' ')[0]}</h1>
          <p className="text-sm font-medium text-primary">Nivel: {rango ?? '—'}</p>
        </div>
        <div className="flex items-center gap-2 rounded-boton bg-tertiary-container px-3 py-2 text-on-tertiary-container">
          <Flame size={28} aria-hidden="true" />
          <div className="leading-tight">
            <p className="text-xs">Racha</p>
            <p className="font-titulo text-sm font-bold">{estadisticas ? `${estadisticas.racha_victoria_actual} victorias` : '—'}</p>
          </div>
        </div>
      </header>

      {hayDemostracion && (
        <button
          type="button"
          onClick={() => irA('/demostracion')}
          className="flex items-center gap-3 rounded-tarjeta bg-secondary-container px-4 py-3 text-left text-on-secondary-container"
        >
          <Radio size={20} aria-hidden="true" />
          <span className="text-sm font-semibold">Hay una demostración en vivo. Toca para verla.</span>
        </button>
      )}

      <PartidaPendiente alTerminar={() => void cargar()} />

      <div className="flex flex-col gap-3 rounded-tarjeta bg-linear-to-br from-primary to-on-primary-fixed-variant p-5 text-on-primary shadow-lg shadow-primary/30">
        <h2 className="font-titulo text-2xl font-bold">Es tu turno de jugar</h2>
        <p className="text-sm text-primary-fixed">Enfréntate a la IA y sigue mejorando tu nivel de ajedrez.</p>
        <BotonPrimario variante="secundario" anchoCompleto={false} className="mt-1 self-start" onClick={() => irA('/jugar')}>
          <Play size={20} aria-hidden="true" /> Jugar
        </BotonPrimario>
      </div>

      {error && <ErrorReintentar mensaje={error} onReintentar={() => void cargar()} />}
      {cargando && sinDatos && <Cargando mensaje="Cargando tus estadísticas…" />}

      <GlassCard className="flex divide-x divide-outline-variant">
        <Estadistica icono={<BarChart3 size={28} className="text-primary" aria-hidden="true" />} etiqueta="Partidas jugadas" valor={estadisticas ? String(estadisticas.total_partidas) : '—'} />
        <Estadistica icono={<Trophy size={28} className="text-primary" aria-hidden="true" />} etiqueta="Victorias" valor={estadisticas ? String(estadisticas.partidas_ganadas) : '—'} />
        <Estadistica
          icono={<Target size={28} className="text-secondary" aria-hidden="true" />}
          etiqueta="Precisión promedio"
          valor={estadisticas && estadisticas.precision_promedio > 0 ? textoPorcentaje(precisionAPorcentaje(estadisticas.precision_promedio)) : '—'}
        />
      </GlassCard>

      <GlassCard className="flex flex-col gap-3">
        <h2 className="font-titulo text-lg font-bold text-on-surface">Mapa de habilidades</h2>
        <RadarHabilidades ejes={ejesDeRadar(estadisticas, usuario)} />
        <ProgresoNivel nivel={nivel} usuario={usuario} />
      </GlassCard>

      <GlassCard className="flex items-center gap-3 bg-primary-container">
        <Quote size={32} className="shrink-0 text-primary" aria-hidden="true" />
        <p className="font-titulo text-lg font-semibold text-on-primary-container">{fraseDelDia()}</p>
      </GlassCard>
    </section>
  );
}
