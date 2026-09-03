import { useState } from "react";
import Tablero from "./Tablero.jsx";
import { crearPartida, moverPartida } from "../api.js";
import { esPromocionDePeon, extraerCasillaDestino, POSICION_INICIAL_FEN } from "../ajedrez.js";

const NIVEL_MIN = 0;
const NIVEL_MAX = 20;

export default function Partida() {
  const [partidaId, setPartidaId] = useState(null);
  const [fen, setFen] = useState(POSICION_INICIAL_FEN);
  const [nivel, setNivel] = useState(NIVEL_MAX);
  const [turno, setTurno] = useState('Presioná «Nueva partida» para empezar.');
  const [casillaResaltada, setCasillaResaltada] = useState(null);
  const [error, setError] = useState(null);

  async function manejarNuevaPartida() {
    setError(null);
    setCasillaResaltada(null);
    const datos = await crearPartida(nivel);
    setPartidaId(datos.id);
    setFen(datos.fen);
    setTurno("Jugás con blancas. Elegí una pieza para mover.");
  }

  async function manejarJugarCasilla(origen, destino) {
    if (!partidaId) return;
    setError(null);
    const jugada = origen + destino + (esPromocionDePeon(fen, origen, destino) ? "q" : "");
    try {
      const datos = await moverPartida(partidaId, jugada);
      setFen(datos.fen);
      setCasillaResaltada(datos.jugada_motor ? extraerCasillaDestino(datos.jugada_motor) : null);
      if (datos.terminada) {
        setTurno(`Partida terminada (${datos.resultado}).`);
      } else if (datos.jugada_motor) {
        setTurno(`Stockfish jugó ${datos.jugada_motor}. Tu turno.`);
      } else {
        setTurno("Tu turno.");
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="mesa" aria-labelledby="tituloPartida">
      <div className="mesa-encabezado">
        <h1 id="tituloPartida">Partida contra Stockfish</h1>
        <p className="estado-turno">{turno}</p>
      </div>

      <Tablero fen={fen} casillaResaltada={casillaResaltada} onJugarCasilla={manejarJugarCasilla} />

      <div className="mesa-controles">
        <label htmlFor="partidaNivelSelect">Nivel de Stockfish</label>
        <select
          id="partidaNivelSelect"
          value={nivel}
          onChange={(evento) => setNivel(Number(evento.target.value))}
        >
          {Array.from({ length: NIVEL_MAX - NIVEL_MIN + 1 }, (_, i) => NIVEL_MIN + i).map((valor) => (
            <option key={valor} value={valor}>
              {valor}
            </option>
          ))}
        </select>
        <button type="button" onClick={manejarNuevaPartida}>
          Nueva partida
        </button>
      </div>

      {error && <p className="aviso">{error}</p>}
    </section>
  );
}
