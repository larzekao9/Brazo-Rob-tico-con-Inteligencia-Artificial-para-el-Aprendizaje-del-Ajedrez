const fenInput = document.getElementById("fenInput");
const nivelSelect = document.getElementById("nivelSelect");
const calcularJugadaBtn = document.getElementById("calcularJugadaBtn");
const analizarPosicionBtn = document.getElementById("analizarPosicionBtn");
const resultadoJugada = document.getElementById("resultadoJugada");
const analisisJugada = document.getElementById("analisisJugada");
const analisisEvaluacion = document.getElementById("analisisEvaluacion");
const analisisMate = document.getElementById("analisisMate");
const mensajeError = document.getElementById("mensajeError");

const partidaNivelSelect = document.getElementById("partidaNivelSelect");
const nuevaPartidaBtn = document.getElementById("nuevaPartidaBtn");
const turnoPartida = document.getElementById("turnoPartida");
const tableroJuego = document.getElementById("tableroJuego");
const mensajePartida = document.getElementById("mensajePartida");

const PIEZA_A_SIMBOLO = {
    P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", K: "♔",
    p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚",
};

let partidaId = null;
let ultimoFenPartida = null;
let casillaOrigenSeleccionada = null;

function poblarSelectDeNiveles(selectElemento) {
    const nivelMin = window.NIVEL_MIN ?? 0;
    const nivelMax = window.NIVEL_MAX ?? 20;
    const nivelDefault = window.NIVEL_DEFAULT ?? nivelMax;
    for (let nivel = nivelMin; nivel <= nivelMax; nivel += 1) {
        const opcion = document.createElement("option");
        opcion.value = String(nivel);
        opcion.textContent = String(nivel);
        if (nivel === nivelDefault) {
            opcion.selected = true;
        }
        selectElemento.appendChild(opcion);
    }
}

function ocultarError() {
    mensajeError.hidden = true;
    mensajeError.textContent = "";
}

function mostrarError(mensaje) {
    mensajeError.hidden = false;
    mensajeError.textContent = mensaje;
}

async function solicitarPosicion(endpoint) {
    const cuerpo = {
        fen: fenInput.value.trim(),
        nivel: Number(nivelSelect.value),
    };
    const respuesta = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo),
    });
    if (!respuesta.ok) {
        const detalle = await respuesta.json().catch(() => null);
        throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
    }
    return respuesta.json();
}

async function calcularJugada() {
    ocultarError();
    calcularJugadaBtn.disabled = true;
    try {
        const datos = await solicitarPosicion("/jugada");
        resultadoJugada.textContent = datos.jugada;
    } catch (error) {
        mostrarError(error.message);
    } finally {
        calcularJugadaBtn.disabled = false;
    }
}

async function analizarPosicion() {
    ocultarError();
    analizarPosicionBtn.disabled = true;
    try {
        const datos = await solicitarPosicion("/analisis");
        analisisJugada.textContent = datos.jugada ?? "-";
        analisisEvaluacion.textContent = datos.evaluacion_cp ?? "-";
        analisisMate.textContent = datos.mate_en ?? "-";
    } catch (error) {
        mostrarError(error.message);
    } finally {
        analizarPosicionBtn.disabled = false;
    }
}

function ocultarMensajePartida() {
    mensajePartida.hidden = true;
    mensajePartida.textContent = "";
}

function mostrarMensajePartida(mensaje) {
    mensajePartida.hidden = false;
    mensajePartida.textContent = mensaje;
}

function fenAMatriz(fen) {
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

function nombreCasilla(fila, columna) {
    const letra = "abcdefgh"[columna];
    const numero = 8 - fila;
    return `${letra}${numero}`;
}

function renderizarTablero(fen) {
    const matriz = fenAMatriz(fen);
    tableroJuego.innerHTML = "";
    for (let fila = 0; fila < 8; fila += 1) {
        for (let columna = 0; columna < 8; columna += 1) {
            const casilla = document.createElement("div");
            const clara = (fila + columna) % 2 === 0;
            casilla.className = `casilla ${clara ? "clara" : "oscura"}`;
            const nombre = nombreCasilla(fila, columna);
            casilla.dataset.casilla = nombre;
            const pieza = matriz[fila][columna];
            if (pieza) {
                casilla.textContent = PIEZA_A_SIMBOLO[pieza];
            }
            casilla.addEventListener("click", () => manejarClicCasilla(nombre));
            tableroJuego.appendChild(casilla);
        }
    }
}

function limpiarSeleccion() {
    casillaOrigenSeleccionada = null;
    tableroJuego.querySelectorAll(".seleccionada").forEach((el) => el.classList.remove("seleccionada"));
}

function manejarClicCasilla(casilla) {
    if (!partidaId) {
        return;
    }
    if (!casillaOrigenSeleccionada) {
        casillaOrigenSeleccionada = casilla;
        tableroJuego.querySelector(`[data-casilla="${casilla}"]`).classList.add("seleccionada");
        return;
    }
    const origen = casillaOrigenSeleccionada;
    const destino = casilla;
    limpiarSeleccion();
    if (origen !== destino) {
        moverPartida(origen, destino);
    }
}

function esPromocionDePeon(origen, destino) {
    const matriz = fenAMatriz(ultimoFenPartida);
    const columna = "abcdefgh".indexOf(origen[0]);
    const fila = 8 - Number(origen[1]);
    const pieza = matriz[fila][columna];
    const promocionBlancas = pieza === "P" && origen[1] === "7" && destino.endsWith("8");
    const promocionNegras = pieza === "p" && origen[1] === "2" && destino.endsWith("1");
    return promocionBlancas || promocionNegras;
}

async function moverPartida(origen, destino) {
    ocultarMensajePartida();
    const jugadaUci = origen + destino + (esPromocionDePeon(origen, destino) ? "q" : "");
    try {
        const respuesta = await fetch(`/partida/${partidaId}/mover`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jugada: jugadaUci }),
        });
        if (!respuesta.ok) {
            const detalle = await respuesta.json().catch(() => null);
            throw new Error(detalle?.detail ?? `Error ${respuesta.status}`);
        }
        const datos = await respuesta.json();
        ultimoFenPartida = datos.fen;
        renderizarTablero(datos.fen);
        if (datos.terminada) {
            turnoPartida.textContent = `Partida terminada (${datos.resultado})`;
        } else {
            turnoPartida.textContent = datos.jugada_motor
                ? `Stockfish jugó: ${datos.jugada_motor}. Tu turno.`
                : "Tu turno.";
        }
    } catch (error) {
        mostrarMensajePartida(error.message);
    }
}

async function nuevaPartida() {
    ocultarMensajePartida();
    limpiarSeleccion();
    const respuesta = await fetch("/partida", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nivel: Number(partidaNivelSelect.value) }),
    });
    const datos = await respuesta.json();
    partidaId = datos.id;
    ultimoFenPartida = datos.fen;
    renderizarTablero(datos.fen);
    turnoPartida.textContent = "Jugás con blancas — tu turno.";
}

calcularJugadaBtn.addEventListener("click", calcularJugada);
analizarPosicionBtn.addEventListener("click", analizarPosicion);
nuevaPartidaBtn.addEventListener("click", nuevaPartida);

poblarSelectDeNiveles(nivelSelect);
poblarSelectDeNiveles(partidaNivelSelect);
