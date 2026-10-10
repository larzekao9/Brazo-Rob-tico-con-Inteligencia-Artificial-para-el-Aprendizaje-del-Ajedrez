// Copia de frontend/src/ajedrez.js (ver PLAN_FRONT_APP.md §2.3). Mantener alineado con el original.
export const POSICION_INICIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export const PIEZA_A_SIMBOLO = {
  P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", K: "♔",
  p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚",
};

const LETRA_A_TIPO = {
  p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king",
};

export function fenAMatriz(fen) {
  const filasFen = fen.split(" ")[0].split("/");
  return filasFen.map((filaFen) => {
    const fila = [];
    for (const caracter of filaFen) {
      if (/[1-8]/.test(caracter)) {
        fila.push(...Array(Number(caracter)).fill(null));
      } else {
        fila.push(caracter);
      }
    }
    return fila;
  });
}

export function nombreCasilla(fila, columna) {
  const letra = "abcdefgh"[columna];
  const numero = 8 - fila;
  return `${letra}${numero}`;
}

export function claseDePieza(caracterFen) {
  const color = caracterFen === caracterFen.toUpperCase() ? "white-piece" : "black-piece";
  const tipo = LETRA_A_TIPO[caracterFen.toLowerCase()];
  return `chess-piece ${color} ${tipo}`;
}

/**
 * Ruta del ícono SVG de la pieza (set "cburnett", el mismo que usa lichess.org —
 * Colin M.L. Burnett, GPLv2+ — ver frontend/public/piezas/). Ej.: "K" -> "/piezas/wK.svg".
 */
export function rutaImagenPieza(caracterFen) {
  const color = caracterFen === caracterFen.toUpperCase() ? "w" : "b";
  return `/piezas/${color}${caracterFen.toUpperCase()}.svg`;
}

export function turnoDeFen(fen) {
  return fen.split(" ")[1] === "b" ? "b" : "w";
}

export function piezaEnCasilla(fen, casilla) {
  const matriz = fenAMatriz(fen);
  const columna = "abcdefgh".indexOf(casilla[0]);
  const fila = 8 - Number(casilla[1]);
  return matriz[fila]?.[columna] ?? null;
}

export function esPromocionDePeon(fen, origen, destino) {
  const matriz = fenAMatriz(fen);
  const columna = "abcdefgh".indexOf(origen[0]);
  const fila = 8 - Number(origen[1]);
  const pieza = matriz[fila]?.[columna];
  const promocionBlancas = pieza === "P" && origen[1] === "7" && destino.endsWith("8");
  const promocionNegras = pieza === "p" && origen[1] === "2" && destino.endsWith("1");
  return promocionBlancas || promocionNegras;
}

export function extraerCasillaDestino(san) {
  const coincidencia = san.replace(/[+#]/g, "").match(/[a-h][1-8](?:=[QRBN])?$/);
  return coincidencia ? coincidencia[0].slice(0, 2) : null;
}

/**
 * Compara dos FEN y devuelve, de forma heurística, qué piezas "se movieron"
 * de una casilla a otra — pensado solo para animación (deslizamiento visual
 * de SalaControl.jsx), nunca para decidir jugadas legales ni nada que
 * dependa de reglas de ajedrez reales.
 *
 * Empareja cada casilla que quedó vacía con una casilla que ganó una pieza
 * del MISMO tipo/color (maneja así una jugada simple y también el enroque,
 * que vacía y ocupa dos pares de casillas a la vez). Si sobra algún cambio
 * sin pareja de la misma letra, lo empareja igual como probable promoción
 * (peón que vacía su casilla y una dama/torre/alfil/caballo que aparece).
 *
 * Una casilla que tenía una pieza y ahora tiene OTRA distinta (captura
 * directa, sin pasar por "vacía" en este diff) cuenta solo como "ocupada"
 * por la pieza nueva — la que estaba antes ahí fue capturada, no se movió a
 * ningún lado, así que no hace falta encontrarle pareja.
 *
 * Devuelve `[]` (nada que animar, se cae al salto instantáneo de siempre)
 * cuando:
 *   - no cambió ninguna casilla,
 *   - cambiaron demasiadas a la vez (`> límiteCambios`) — típico de cargar
 *     una partida nueva o una posición escaneada por cámara, no de una
 *     jugada — animar ahí sería ruido, no ayuda,
 *   - queda una casilla "ocupada" sin explicar al terminar (algo no encaja
 *     con el patrón esperado de una jugada) — más vale no animar que animar
 *     mal. Una "vaciada" sin pareja SÍ es normal y esperable (una captura o
 *     una captura al paso: la pieza tomada solo desaparece).
 */
export function detectarMovimientosVisuales(fenAnterior, fenNuevo, limiteCambios = 4) {
  if (!fenAnterior || !fenNuevo || fenAnterior === fenNuevo) return [];

  const matrizAnterior = fenAMatriz(fenAnterior);
  const matrizNueva = fenAMatriz(fenNuevo);
  const vaciadas = []; // { casilla, pieza } — piezas que dejaron de estar ahí
  const ocupadas = []; // { casilla, pieza } — piezas que aparecieron ahí

  for (let fila = 0; fila < 8; fila++) {
    for (let columna = 0; columna < 8; columna++) {
      const antes = matrizAnterior[fila]?.[columna] ?? null;
      const despues = matrizNueva[fila]?.[columna] ?? null;
      if (antes === despues) continue;
      const casilla = nombreCasilla(fila, columna);
      if (antes && !despues) {
        vaciadas.push({ casilla, pieza: antes });
      } else if (despues) {
        // Cubre "estaba vacía y ahora tiene pieza" y "tenía una pieza y
        // ahora tiene otra" (captura directa) por igual.
        ocupadas.push({ casilla, pieza: despues });
      }
    }
  }

  const totalCambios = vaciadas.length + ocupadas.length;
  if (totalCambios === 0 || totalCambios > limiteCambios) return [];

  const ocupadasRestantes = [...ocupadas];
  const movimientos = [];
  const sinPareja = [];

  for (const origen of vaciadas) {
    const indice = ocupadasRestantes.findIndex((o) => o.pieza === origen.pieza);
    if (indice === -1) {
      sinPareja.push(origen);
      continue;
    }
    const [destino] = ocupadasRestantes.splice(indice, 1);
    if (origen.casilla !== destino.casilla) {
      movimientos.push({ casillaOrigen: origen.casilla, casillaDestino: destino.casilla, pieza: destino.pieza });
    }
  }

  // Sobras: probablemente una promoción (el peón "vaciado" no matchea por
  // letra con la pieza nueva). Si sobra justo un origen y un destino, se
  // asume que es esa jugada — mostrar la pieza YA promocionada volando es
  // una simplificación aceptable para una animación, no para el motor.
  if (sinPareja.length === 1 && ocupadasRestantes.length === 1) {
    const [origen] = sinPareja;
    const [destino] = ocupadasRestantes;
    if (origen.casilla !== destino.casilla) {
      movimientos.push({ casillaOrigen: origen.casilla, casillaDestino: destino.casilla, pieza: destino.pieza });
    }
  } else if (ocupadasRestantes.length > 0) {
    // Queda una casilla ocupada sin ninguna explicación razonable (no es una
    // promoción 1-a-1) — no encaja con el patrón esperado de una jugada,
    // mejor no animar nada que animar algo incorrecto. Un `sinPareja` sobrante
    // por sí solo (sin `ocupadasRestantes`) es normal — son piezas
    // capturadas, no necesitan destino.
    return [];
  }

  return movimientos;
}

/**
 * Casillas de movimiento ILUSTRATIVAS para una pieza parada sola en un
 * mini-tablero vacío (Panel de Aprendizaje, "Aprendé cada pieza") — reglas
 * simplificadas por tipo de pieza, sin capturas ni jaques ni reglas
 * especiales (enroque, al paso). No es el motor real: solo sirve para
 * mostrar de un vistazo hacia dónde se mueve cada pieza. `fila`/`columna`
 * van de 0 a 7 (igual que las filas de `fenAMatriz`, fila 0 = octava fila).
 */
export function casillasIlustrativas(tipoPieza, fila, columna) {
  const dentroDelTablero = (f, c) => f >= 0 && f < 8 && c >= 0 && c < 8;
  const resultado = [];
  const agregar = (f, c) => {
    if (dentroDelTablero(f, c)) resultado.push([f, c]);
  };

  switch (tipoPieza) {
    case "peon":
      // Ilustrativo: un paso "hacia adelante" (hacia fila 0, como las blancas en `fenAMatriz`).
      agregar(fila - 1, columna);
      break;
    case "caballo":
      [[-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1]].forEach(([df, dc]) =>
        agregar(fila + df, columna + dc)
      );
      break;
    case "alfil":
      for (let d = 1; d < 8; d++) {
        agregar(fila - d, columna - d);
        agregar(fila - d, columna + d);
        agregar(fila + d, columna - d);
        agregar(fila + d, columna + d);
      }
      break;
    case "torre":
      for (let d = 0; d < 8; d++) {
        if (d !== fila) agregar(d, columna);
        if (d !== columna) agregar(fila, d);
      }
      break;
    case "dama":
      return [...casillasIlustrativas("torre", fila, columna), ...casillasIlustrativas("alfil", fila, columna)];
    case "rey":
      for (let df = -1; df <= 1; df++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (df !== 0 || dc !== 0) agregar(fila + df, columna + dc);
        }
      }
      break;
    default:
      break;
  }
  return resultado;
}
