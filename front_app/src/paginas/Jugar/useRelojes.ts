import {useEffect, useState} from 'react';
import type {Color} from '../../dominio/tablero';

/**
 * Tiempo transcurrido de cada bando. El backend no tiene control de tiempo, así que los
 * relojes solo cuentan cuánto lleva pensando quien tiene el turno (sin límite ni derrota por tiempo).
 */
export function useRelojes(turno: Color, activo: boolean, reinicio: string): Record<Color, number> {
  const [segundos, setSegundos] = useState<Record<Color, number>>({w: 0, b: 0});

  useEffect(() => {
    setSegundos({w: 0, b: 0});
  }, [reinicio]);

  useEffect(() => {
    if (!activo) return;
    const intervalo = setInterval(() => setSegundos((previo) => ({...previo, [turno]: previo[turno] + 1})), 1000);
    return () => clearInterval(intervalo);
  }, [turno, activo]);

  return segundos;
}
