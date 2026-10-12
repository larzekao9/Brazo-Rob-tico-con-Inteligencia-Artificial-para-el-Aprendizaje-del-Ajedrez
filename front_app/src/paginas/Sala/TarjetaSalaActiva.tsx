import {useEffect, useState} from 'react';
import {Play} from 'lucide-react';
import {salaActiva} from '../../api/sala';
import BotonPrimario from '../../componentes/BotonPrimario';
import GlassCard from '../../componentes/GlassCard';
import {irA} from '../../router';
import BotonCancelarSala from './BotonCancelarSala';
import type {SalaActiva} from './tipos';

/** Texto de la tarjeta: "Sala K7M2QX · esperando rival" o "Partida con Ana en curso". */
function descripcion(sala: SalaActiva): string {
  if (sala.estado === 'esperando') return `Sala ${sala.codigo} · esperando rival`;
  const rival = sala.rol === 'negras' ? sala.blancas : sala.negras;
  return rival ? `Partida con ${rival.nombre} en curso` : `Sala ${sala.codigo} en curso`;
}

/**
 * Tarjeta de la sala activa del usuario (GET /sala/activa, `null` si no hay): "Entrar" y, si todavía
 * espera rival, "Cancelar sala". Es opcional: si la consulta falla simplemente no se muestra.
 */
export default function TarjetaSalaActiva() {
  const [sala, setSala] = useState<SalaActiva | null>(null);

  useEffect(() => {
    let activo = true;
    salaActiva()
      .then((s: SalaActiva | null) => {
        if (activo) setSala(s);
      })
      .catch(() => {
        if (activo) setSala(null);
      });
    return () => {
      activo = false;
    };
  }, []);

  if (!sala) return null;
  return (
    <GlassCard className="flex flex-col gap-3 border-primary/40">
      <div>
        <h2 className="font-titulo text-lg font-bold text-on-surface">Tienes una sala con un amigo</h2>
        <p className="text-sm text-on-surface-variant">{descripcion(sala)}</p>
      </div>
      <BotonPrimario onClick={() => irA('/sala/:codigo', {codigo: sala.codigo})}>
        <Play size={18} aria-hidden="true" /> Entrar
      </BotonPrimario>
      {sala.estado === 'esperando' && <BotonCancelarSala codigo={sala.codigo} alCancelar={() => setSala(null)} />}
    </GlassCard>
  );
}
