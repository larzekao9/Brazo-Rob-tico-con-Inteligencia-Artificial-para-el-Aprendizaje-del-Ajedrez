import BotonPrimario from './BotonPrimario';

interface Props {
  mensaje: string;
  onReintentar?: () => void;
}

/** Aviso de error visible con botón de reintento opcional (nunca falla en silencio). */
export default function ErrorReintentar({mensaje, onReintentar}: Props) {
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-tarjeta border border-error/30 bg-error-container p-4 text-on-error-container">
      <p className="text-sm font-medium">{mensaje}</p>
      {onReintentar && (
        <BotonPrimario variante="secundario" onClick={onReintentar} anchoCompleto={false} className="self-start">
          Reintentar
        </BotonPrimario>
      )}
    </div>
  );
}
