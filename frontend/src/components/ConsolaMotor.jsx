import { useState } from "react";
import { calcularJugada, analizarPosicion } from "../api.js";
import { POSICION_INICIAL_FEN } from "../ajedrez.js";

const NIVEL_MIN = 0;
const NIVEL_MAX = 20;

export default function ConsolaMotor() {
  const [fen, setFen] = useState(POSICION_INICIAL_FEN);
  const [nivel, setNivel] = useState(NIVEL_MAX);
  const [jugadaCalculada, setJugadaCalculada] = useState("—");
  const [analisis, setAnalisis] = useState({ jugada: "—", evaluacion_cp: "—", mate_en: "—" });
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(null);

  async function manejarCalcular() {
    setError(null);
    setCargando("calcular");
    try {
      const datos = await calcularJugada(fen.trim(), nivel);
      setJugadaCalculada(datos.jugada);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(null);
    }
  }

  async function manejarAnalizar() {
    setError(null);
    setCargando("analizar");
    try {
      const datos = await analizarPosicion(fen.trim(), nivel);
      setAnalisis({
        jugada: datos.jugada ?? "—",
        evaluacion_cp: datos.evaluacion_cp ?? "—",
        mate_en: datos.mate_en ?? "—",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(null);
    }
  }

  return (
    <aside className="consola" aria-labelledby="tituloConsola">
      <h2 id="tituloConsola">Consola del motor</h2>

      <div className="consola-grupo">
        <label htmlFor="fenInput">Posición (FEN)</label>
        <input
          id="fenInput"
          type="text"
          value={fen}
          onChange={(evento) => setFen(evento.target.value)}
          autoComplete="off"
          spellCheck="false"
        />

        <label htmlFor="nivelSelect">Nivel</label>
        <select
          id="nivelSelect"
          value={nivel}
          onChange={(evento) => setNivel(Number(evento.target.value))}
        >
          {Array.from({ length: NIVEL_MAX - NIVEL_MIN + 1 }, (_, i) => NIVEL_MIN + i).map((valor) => (
            <option key={valor} value={valor}>
              {valor}
            </option>
          ))}
        </select>

        <div className="consola-acciones">
          <button type="button" onClick={manejarCalcular} disabled={cargando === "calcular"}>
            Calcular jugada
          </button>
          <button type="button" onClick={manejarAnalizar} disabled={cargando === "analizar"}>
            Analizar posición
          </button>
        </div>
      </div>

      <dl className="lecturas">
        <div className="lectura">
          <dt>Jugada calculada</dt>
          <dd>{jugadaCalculada}</dd>
        </div>
        <div className="lectura">
          <dt>Jugada sugerida</dt>
          <dd>{analisis.jugada}</dd>
        </div>
        <div className="lectura">
          <dt>Evaluación (cp)</dt>
          <dd>{analisis.evaluacion_cp}</dd>
        </div>
        <div className="lectura">
          <dt>Mate en</dt>
          <dd>{analisis.mate_en}</dd>
        </div>
      </dl>

      {error && <p className="aviso">{error}</p>}
    </aside>
  );
}
