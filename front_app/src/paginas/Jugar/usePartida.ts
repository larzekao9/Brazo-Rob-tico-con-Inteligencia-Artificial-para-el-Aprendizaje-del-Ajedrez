import {useCallback, useEffect, useState} from 'react';
import {analizarPosicion, moverPartida, obtenerJugadasLegales, obtenerPartida} from '../../api/backend';
import {extraerCasillaDestino} from '../../dominio/ajedrez';
import {
  evaluacionDeRespuesta,
  evaluacionDesdeBlancas,
  ultimaJugadaDeSan,
  type EstadoPartida,
  type Evaluacion,
  type RespuestaMover,
} from './partidaUtil';

const mensajeDe = (err: unknown, porDefecto: string) => (err instanceof Error ? err.message : porDefecto);

/** Carga una partida del backend y aplica las jugadas del jugador; la respuesta de la IA llega en el mismo POST /mover. */
export function usePartida(id: string) {
  const [partida, setPartida] = useState<EstadoPartida | null>(null);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);
  const [errorJugada, setErrorJugada] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(null);
  const [probabilidadVictoria, setProbabilidadVictoria] = useState<number | null>(null);
  const [ultimaJugada, setUltimaJugada] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setErrorCarga(null);
    try {
      const datos = (await obtenerPartida(id)) as EstadoPartida;
      setPartida(datos);
      setEvaluacion(null);
      setProbabilidadVictoria(null);
      setUltimaJugada(null);
      // Al retomar no hay evaluación previa: se pide una para no dejar la barra vacía.
      if (!datos.terminada && datos.jugadas.length > 0) {
        analizarPosicion(datos.fen, datos.nivel)
          .then((a: {evaluacion_cp: number | null; mate_en: number | null}) =>
            setEvaluacion(evaluacionDesdeBlancas(datos.fen, a.evaluacion_cp, a.mate_en)),
          )
          .catch(() => setEvaluacion(null)); // la barra queda en "Sin evaluación"
      }
    } catch (err) {
      setPartida(null);
      setErrorCarga(mensajeDe(err, 'No se pudo cargar la partida.'));
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const mover = useCallback(
    async (jugadaUci: string) => {
      setEnviando(true);
      setErrorJugada(null);
      try {
        const r = (await moverPartida(id, jugadaUci)) as RespuestaMover;
        setPartida((previa) => (previa ? {...previa, fen: r.fen, jugadas: r.jugadas, terminada: r.terminada, resultado: r.resultado} : previa));
        setEvaluacion(evaluacionDeRespuesta(r));
        setProbabilidadVictoria(r.retroalimentacion_en_vivo?.probabilidad_victoria ?? null);
        setUltimaJugada(ultimaJugadaDeSan(r.jugada_motor ? extraerCasillaDestino(r.jugada_motor) : null));
      } catch (err) {
        setErrorJugada(mensajeDe(err, 'No se pudo aplicar la jugada.'));
      } finally {
        setEnviando(false);
      }
    },
    [id],
  );

  const obtenerDestinos = useCallback(async (casilla: string) => (await obtenerJugadasLegales(id, casilla)).casillas as string[], [id]);

  return {partida, cargando, errorCarga, errorJugada, setErrorJugada, enviando, evaluacion, probabilidadVictoria, ultimaJugada, cargar, mover, obtenerDestinos};
}
