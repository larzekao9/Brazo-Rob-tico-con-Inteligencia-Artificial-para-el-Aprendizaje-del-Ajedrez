import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import ErrorReintentar from '../../componentes/ErrorReintentar';
import {irA, useRuta} from '../../router';
import SalaEsperando from './SalaEsperando';
import SalaTablero from './SalaTablero';
import {useSala} from './useSala';

/** /sala/:codigo: orquesta esperando / jugando / espectador / terminada según el estado real de la sala. */
export default function Sala() {
  const {params} = useRuta();
  const codigo = params.codigo ?? '';
  const {sala, cargando, error, reconectando, reintentar, aplicarSala} = useSala(codigo);

  if (cargando) return <Cargando mensaje="Entrando a la sala…" />;
  if (error || !sala) {
    return (
      <section className="flex flex-col gap-3 p-4">
        <ErrorReintentar mensaje={error?.mensaje ?? 'No se pudo cargar la sala.'} onReintentar={error?.sinConexion === false ? undefined : reintentar} />
        <BotonPrimario variante="secundario" onClick={() => irA('/inicio')}>
          Volver al inicio
        </BotonPrimario>
      </section>
    );
  }
  if (sala.estado === 'esperando') return <SalaEsperando sala={sala} />;
  return <SalaTablero sala={sala} aplicarSala={aplicarSala} reconectando={reconectando} />;
}
