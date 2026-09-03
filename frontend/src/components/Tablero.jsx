import { useState } from "react";
import { fenAMatriz, nombreCasilla, PIEZA_A_SIMBOLO } from "../ajedrez.js";

export default function Tablero({ fen, casillaResaltada, onJugarCasilla }) {
  const [origenSeleccionado, setOrigenSeleccionado] = useState(null);
  const matriz = fenAMatriz(fen);

  function manejarClic(casilla) {
    if (!origenSeleccionado) {
      setOrigenSeleccionado(casilla);
      return;
    }
    const origen = origenSeleccionado;
    setOrigenSeleccionado(null);
    if (origen !== casilla) {
      onJugarCasilla(origen, casilla);
    }
  }

  const casillas = [];
  for (let fila = 0; fila < 8; fila += 1) {
    for (let columna = 0; columna < 8; columna += 1) {
      const nombre = nombreCasilla(fila, columna);
      const clara = (fila + columna) % 2 === 0;
      const pieza = matriz[fila][columna];
      const clases = ["casilla", clara ? "clara" : "oscura"];
      if (nombre === origenSeleccionado) clases.push("seleccionada");
      if (nombre === casillaResaltada) clases.push("resaltada");

      casillas.push(
        <button
          key={nombre}
          type="button"
          className={clases.join(" ")}
          onClick={() => manejarClic(nombre)}
          aria-label={`Casilla ${nombre}${pieza ? `, pieza ${pieza}` : ", vacía"}`}
        >
          {pieza ? PIEZA_A_SIMBOLO[pieza] : ""}
          {columna === 0 && <span className="coordenada coordenada-fila">{8 - fila}</span>}
          {fila === 7 && <span className="coordenada coordenada-columna">{"abcdefgh"[columna]}</span>}
        </button>,
      );
    }
  }

  return (
    <div className="tablero-envoltorio">
      <div className="tablero" role="grid" aria-label="Tablero de ajedrez">
        {casillas}
      </div>
    </div>
  );
}
