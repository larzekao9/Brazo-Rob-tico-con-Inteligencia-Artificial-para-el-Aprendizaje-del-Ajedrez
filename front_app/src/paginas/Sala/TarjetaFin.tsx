import BotonPrimario from '../../componentes/BotonPrimario';
import GlassCard from '../../componentes/GlassCard';
import {irA} from '../../router';
import {textoDeFin} from './salaUtil';
import type {SalaEstado} from './tipos';

const ESTILO_POR_TONO = {
  victoria: 'border-primary bg-primary-container text-on-primary-container',
  derrota: 'border-error/40 bg-error-container text-on-error-container',
  neutro: 'border-outline-variant bg-surface-low text-on-surface',
} as const;

/** Tarjeta de fin de partida: veredicto según quién mira, "Ver análisis" y "Volver al inicio". */
export default function TarjetaFin({sala}: {sala: SalaEstado}) {
  const fin = textoDeFin(sala);
  const hayAnalisis = sala.jugadas.length > 0;
  return (
    <GlassCard className={`flex flex-col gap-3 ${ESTILO_POR_TONO[fin.tono]}`}>
      <h2 className="font-titulo text-xl font-bold">{fin.titulo}</h2>
      <p className="text-sm">{fin.detalle}</p>
      {sala.resultado && <p className="text-xs opacity-80">Resultado: {sala.resultado}</p>}
      {hayAnalisis && <BotonPrimario onClick={() => irA('/sala/:codigo/analisis', {codigo: sala.codigo})}>Ver análisis</BotonPrimario>}
      <BotonPrimario variante="secundario" onClick={() => irA('/inicio')}>
        Volver al inicio
      </BotonPrimario>
    </GlassCard>
  );
}
