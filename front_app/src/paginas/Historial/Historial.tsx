import {useCallback, useEffect, useState} from 'react';
import {Clock, Plus, Search, Play} from 'lucide-react';
import {irA} from '../../router';
import {historialPartidasPropio} from '../../api/backend';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import ErrorReintentar from '../../componentes/ErrorReintentar';

/** Forma real de `GET /usuario/historial-partidas` (backend/rutas/ruta_usuario.py). */
interface PartidaHistorial {
  id: string;
  fecha: string;
  resultado: string | null;
  tipo_oponente: string;
  nivel: number;
  cantidad_jugadas: number;
  estado: 'en_curso' | 'terminada' | string;
}

const LIMITE = 10;

/** El jugador siempre lleva blancas (POST /partida no acepta color). */
function textoResultado(p: PartidaHistorial): {texto: string; clase: string} {
  if (p.estado !== 'terminada') return {texto: 'En curso', clase: 'text-secondary'};
  if (p.resultado === '1-0') return {texto: 'Victoria', clase: 'text-primary'};
  if (p.resultado === '0-1') return {texto: 'Derrota', clase: 'text-error'};
  return {texto: 'Tablas', clase: 'text-on-surface-variant'};
}

function formatearFecha(fecha: string): string {
  const d = new Date(fecha);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('es-ES', {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'});
}

/** Terminada: va al análisis (Resultado). En curso: la retoma. */
function abrir(p: PartidaHistorial): void {
  if (p.estado === 'terminada') irA('/jugar/resultado/:id', {id: p.id});
  else irA('/jugar/partida/:id', {id: p.id});
}

export default function Historial() {
  const [partidas, setPartidas] = useState<PartidaHistorial[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async (offset: number) => {
    if (offset > 0) setCargandoMas(true);
    else setCargando(true);
    setError(null);
    try {
      const data = await historialPartidasPropio(LIMITE, offset);
      const nuevas: PartidaHistorial[] = data?.partidas ?? [];
      setPartidas((previas) => (offset > 0 ? [...previas, ...nuevas] : nuevas));
      setTotal(typeof data?.total === 'number' ? data.total : offset + nuevas.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo cargar el historial.');
    } finally {
      setCargando(false);
      setCargandoMas(false);
    }
  }, []);

  useEffect(() => {
    void cargar(0);
  }, [cargar]);

  return (
    <div className="flex flex-col gap-4 px-4 pb-6 pt-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-titulo text-2xl font-bold text-on-surface">Mis partidas</h1>
          <p className="text-sm text-on-surface-variant">Toca una partida para ver su análisis.</p>
        </div>
        <BotonPrimario anchoCompleto={false} onClick={() => irA('/jugar')}>
          <Plus size={16} aria-hidden="true" /> Nueva
        </BotonPrimario>
      </div>

      {cargando && <Cargando mensaje="Cargando tus partidas…" />}
      {!cargando && error && partidas.length === 0 && <ErrorReintentar mensaje={error} onReintentar={() => void cargar(0)} />}

      {!cargando && !error && partidas.length === 0 && (
        <GlassCard className="py-10 text-center">
          <h2 className="font-titulo text-lg font-bold text-on-surface">Sin partidas aún</h2>
          <p className="mb-5 text-on-surface-variant">Cuando juegues, tus partidas aparecerán aquí.</p>
          <BotonPrimario onClick={() => irA('/jugar')}>Jugar mi primera partida</BotonPrimario>
        </GlassCard>
      )}

      <ul className="flex flex-col gap-3">
        {partidas.map((p) => {
          const {texto, clase} = textoResultado(p);
          const terminada = p.estado === 'terminada';
          return (
            <li key={p.id}>
              <button type="button" onClick={() => abrir(p)} className="w-full text-left">
                <GlassCard className="flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`font-titulo font-bold ${clase}`}>{texto}</span>
                      <span className="text-xs text-on-surface-variant">{p.cantidad_jugadas} jugadas</span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-on-surface-variant">
                      <span className="flex items-center gap-1">
                        <Clock size={12} aria-hidden="true" />
                        {formatearFecha(p.fecha)}
                      </span>
                      <span>{p.tipo_oponente === 'modelo' ? 'Modelo Turing' : 'Stockfish'}</span>
                      <span>Nivel {p.nivel}</span>
                    </div>
                  </div>
                  <span className="flex flex-col items-center text-xs text-primary">
                    {terminada ? <Search size={20} aria-hidden="true" /> : <Play size={20} aria-hidden="true" />}
                    {terminada ? 'Análisis' : 'Retomar'}
                  </span>
                </GlassCard>
              </button>
            </li>
          );
        })}
      </ul>

      {partidas.length < total && (
        <BotonPrimario variante="secundario" cargando={cargandoMas} onClick={() => void cargar(partidas.length)}>
          Cargar más partidas
        </BotonPrimario>
      )}
    </div>
  );
}
