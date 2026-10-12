import {useState} from 'react';
import {X} from 'lucide-react';
import {cancelarSala} from '../../api/sala';
import BotonPrimario from '../../componentes/BotonPrimario';
import {mensajeDeError} from './salaUtil';

interface Props {
  codigo: string;
  /** Se llama cuando el backend confirmó la cancelación (DELETE /sala/{codigo}). */
  alCancelar: () => void;
}

/** "Cancelar sala" con confirmación dentro de la app (sin window.confirm): borra la sala que espera rival. */
export default function BotonCancelarSala({codigo, alCancelar}: Props) {
  const [confirmando, setConfirmando] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmar() {
    setCancelando(true);
    setError(null);
    try {
      await cancelarSala(codigo);
      alCancelar();
    } catch (err) {
      setError(mensajeDeError(err, 'No se pudo cancelar la sala.'));
      setConfirmando(false);
    } finally {
      setCancelando(false);
    }
  }

  if (confirmando) {
    return (
      <div className="flex flex-col gap-2" role="group" aria-label="Confirmar cancelación">
        <p className="text-sm font-medium text-on-surface">¿Cancelar la sala {codigo}? El enlace dejará de funcionar.</p>
        <div className="flex gap-2">
          <BotonPrimario variante="peligro" cargando={cancelando} textoCargando="Cancelando…" onClick={() => void confirmar()}>
            Sí, cancelar
          </BotonPrimario>
          <BotonPrimario variante="secundario" disabled={cancelando} onClick={() => setConfirmando(false)}>
            No, mantener
          </BotonPrimario>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {error && (
        <p role="alert" className="text-sm text-error">
          {error}
        </p>
      )}
      <BotonPrimario variante="secundario" onClick={() => setConfirmando(true)}>
        <X size={18} aria-hidden="true" /> Cancelar sala
      </BotonPrimario>
    </div>
  );
}
