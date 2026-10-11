import {useEffect, useState} from 'react';
import {Check, Hourglass, MapPin, Medal, Target, TrendingUp} from 'lucide-react';
import {obtenerNivelJugador} from '../../../api/backend';
import BotonPrimario from '../../../componentes/BotonPrimario';
import ErrorReintentar from '../../../componentes/ErrorReintentar';
import ProgresoBarra from '../../../componentes/ProgresoBarra';
import {BANDAS_POR_DEFECTO, NIVEL_DIAGNOSTICO, NIVEL_MAX_MODELO, NIVEL_MAX_STOCKFISH, precisionAPorcentaje} from '../../../dominio/nivelJugador';
import type {Usuario} from '../../../estado/SesionContext';
import {irA} from '../../../router';
import GraficaPrecision, {type Calibracion} from './GraficaPrecision';
import {CargandoInline} from './ui';

interface DatosNivel {
  nivel_estimado: number | null;
  rango_estimado: string | null;
  diagnostico_completado?: boolean;
  partidas_calibradas?: number;
  partidas_diagnostico?: number;
  precision_promedio?: number;
  progreso_siguiente_nivel?: number | null;
  precision_siguiente_nivel?: number | null;
  calibraciones?: Calibracion[];
  escala?: {nivel_max?: number; nivel_max_modelo?: number; bandas?: Record<string, [number, number]>};
}

function ChipNivel({n, actual, soloStockfish}: {n: number; actual: number; soloStockfish: boolean}) {
  const estado = n < actual ? 'superado' : n === actual ? 'actual' : 'pendiente';
  const clases = {
    superado: 'border-primary/40 bg-primary-container text-on-primary-container',
    actual: 'border-primary bg-primary font-bold text-on-primary ring-2 ring-primary/40 ring-offset-2 ring-offset-surface-lowest',
    pendiente: 'border-dashed border-outline-variant text-on-surface-variant',
  }[estado];
  const etiqueta = `Nivel ${n}, ${{superado: 'superado', actual: 'tu nivel actual', pendiente: 'pendiente'}[estado]}${soloStockfish ? ', solo existe en Stockfish' : ''}`;
  return (
    <li aria-label={etiqueta} aria-current={estado === 'actual' ? 'step' : undefined} className={`relative flex size-10 items-center justify-center rounded-lg border text-sm ${clases}`}>
      {estado === 'superado' && <Check size={10} className="absolute right-0.5 top-0.5" aria-hidden="true" />}
      <span aria-hidden="true">{n}</span>
      {soloStockfish && (
        <span className="absolute inset-x-0 bottom-0.5 text-center text-[8px] leading-none" aria-hidden="true">
          SF
        </span>
      )}
    </li>
  );
}

function SinMedir({partidasDiagnostico, clase}: {partidasDiagnostico: number; clase: string}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl bg-primary-container p-4">
      <div className="flex items-start gap-3">
        <Target size={28} className="shrink-0 text-primary" aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <h3 className="font-titulo text-lg font-bold text-on-primary-container">Nivel sin medir</h3>
          <p className={`${clase} text-on-primary-container`}>
            Todavía no medimos tu nivel. Juega tus partidas de diagnóstico (contra Stockfish, nivel {NIVEL_DIAGNOSTICO}): después de cada una verás un nivel
            provisional, y con las {partidasDiagnostico} queda confirmado.
          </p>
        </div>
      </div>
      <BotonPrimario onClick={() => irA('/jugar')}>Ir a jugar</BotonPrimario>
    </div>
  );
}

function NivelMedido({datos, clase}: {datos: DatosNivel; clase: string}) {
  const nivel = datos.nivel_estimado ?? 0;
  const escala = datos.escala ?? {};
  const bandas = escala.bandas ?? BANDAS_POR_DEFECTO;
  const nivelMaxModelo = escala.nivel_max_modelo ?? NIVEL_MAX_MODELO;
  const nivelMax = escala.nivel_max ?? NIVEL_MAX_STOCKFISH;
  const hayNivelesSoloStockfish = Object.values(bandas).some(([, hasta]) => hasta > nivelMaxModelo);
  const promedio = precisionAPorcentaje(datos.precision_promedio);
  const calibradas = datos.partidas_calibradas ?? 0;
  const diagnostico = datos.partidas_diagnostico ?? 3;
  const provisional = datos.diagnostico_completado === false;
  const progreso = datos.progreso_siguiente_nivel;
  const requerida = precisionAPorcentaje(datos.precision_siguiente_nivel);

  return (
    <>
      {provisional && (
        <p role="status" className={`flex items-start gap-2 rounded-2xl bg-tertiary-container p-3 text-on-tertiary-container ${clase}`}>
          <Hourglass size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>
            <strong>Nivel provisional:</strong> llevas {calibradas} de {diagnostico} partidas de diagnóstico. Una sola partida mide demasiado al azar; al completar
            las {diagnostico} el nivel queda confirmado.
          </span>
        </p>
      )}

      <div className="flex items-center gap-4 rounded-2xl bg-primary-container p-4">
        <span className="flex size-14 shrink-0 items-center justify-center rounded-full border-2 border-primary bg-surface-lowest text-primary" aria-hidden="true">
          <Medal size={28} />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-on-primary-container">Tu nivel actual</p>
          <h3 className="break-words font-titulo text-2xl font-bold text-on-primary-container">
            Nivel {nivel}
            {datos.rango_estimado ? ` · ${datos.rango_estimado}` : ''}
          </h3>
          <p className="text-xs text-on-primary-container">
            {calibradas > 0 ? `Medido con ${calibradas} ${calibradas === 1 ? 'partida' : 'partidas'}` : 'Medido'}
            {promedio != null ? ` · precisión promedio ${promedio} %` : ''}
          </p>
        </div>
      </div>

      {typeof progreso === 'number' && nivel < nivelMax && (
        <div className="flex flex-col gap-2 rounded-2xl bg-surface-low p-3">
          <p className="flex items-center gap-2 text-sm font-semibold text-on-surface">
            <TrendingUp size={16} className="text-primary" aria-hidden="true" />
            Siguiente nivel: {nivel + 1}
          </p>
          <ProgresoBarra valor={Math.min(1, Math.max(0, progreso)) * 100} etiqueta={`Progreso hacia el nivel ${nivel + 1}`} />
          <p className="text-xs text-on-surface-variant">
            {Math.round(Math.min(1, Math.max(0, progreso)) * 100)} % hacia el nivel {nivel + 1}
            {requerida != null ? ` · necesitas ~${requerida} % de precisión` : ''}
          </p>
        </div>
      )}

      <div className="flex flex-col gap-2">
        <h4 className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">Escalera de niveles</h4>
        {Object.entries(bandas).map(([rango, [desde, hasta]]) => {
          const esActual = nivel >= desde && nivel <= hasta;
          return (
            <div key={rango} className={`flex flex-col gap-2 rounded-2xl border p-3 ${esActual ? 'border-primary bg-primary-container/40' : 'border-outline-variant bg-surface-lowest'}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-1 font-semibold text-on-surface">
                  {esActual && <MapPin size={14} className="text-primary" aria-hidden="true" />}
                  {rango}
                  {esActual && <span className="text-xs font-bold uppercase text-primary">tu rango</span>}
                </span>
                <span className="text-xs text-on-surface-variant">
                  Niveles {desde}-{hasta}
                </span>
              </div>
              <ul className="flex flex-wrap gap-1.5" aria-label={`Niveles de ${rango}`}>
                {Array.from({length: hasta - desde + 1}, (_, i) => desde + i).map((n) => (
                  <ChipNivel key={n} n={n} actual={nivel} soloStockfish={n > nivelMaxModelo} />
                ))}
              </ul>
            </div>
          );
        })}
        {hayNivelesSoloStockfish && (
          <p className="text-xs text-on-surface-variant">
            SF: nivel que solo existe en Stockfish. Turing juega como Maestro hasta el nivel {nivelMaxModelo}; del {nivelMaxModelo + 1} al {nivelMax} el reto es
            Stockfish.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <h4 className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">Precisión de tus últimas partidas</h4>
        <GraficaPrecision calibraciones={datos.calibraciones} partidasCalibradas={calibradas} />
        <p className={`${clase} text-on-surface-variant`}>
          Tu nivel usa el promedio de tus últimas 3 partidas frente a Stockfish; sube cuando mantienes la precisión, no por días.
        </p>
      </div>
    </>
  );
}

/**
 * "Tu nivel": nivel MEDIDO del jugador (el backend compara sus jugadas con las de Stockfish). Nunca inventa un
 * rango: sin diagnóstico lo dice, y si la consulta falla muestra el último rango guardado en el perfil.
 */
export default function TuNivel({usuario, clase}: {usuario: Usuario | null; clase: string}) {
  const [datos, setDatos] = useState<DatosNivel | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    obtenerNivelJugador()
      .then((r: DatosNivel) => vigente && setDatos(r))
      .catch((err: Error) => vigente && setError(err))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [intento]);

  if (cargando && !datos) return <CargandoInline texto="Cargando tu nivel…" />;
  if (error && !datos) {
    return (
      <div className="flex flex-col gap-3">
        <ErrorReintentar mensaje={`No pudimos cargar tu nivel ahora. ${error.message}`} onReintentar={() => setIntento((n) => n + 1)} />
        {usuario?.rango_estimado && (
          <p className="rounded-2xl bg-surface-low p-3 text-sm text-on-surface-variant">
            Último rango guardado: <strong className="text-on-surface">{usuario.rango_estimado}</strong>
          </p>
        )}
      </div>
    );
  }
  if (!datos) return null;

  const sinMedir = datos.nivel_estimado == null || (datos.partidas_calibradas ?? 0) === 0;
  return sinMedir ? <SinMedir partidasDiagnostico={datos.partidas_diagnostico ?? 3} clase={clase} /> : <NivelMedido datos={datos} clase={clase} />;
}
