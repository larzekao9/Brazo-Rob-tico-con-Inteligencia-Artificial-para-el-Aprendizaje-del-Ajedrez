const fenInput = document.getElementById("fenInput");
const nivelSelect = document.getElementById("nivelSelect");
const calcularJugadaBtn = document.getElementById("calcularJugadaBtn");
const analizarPosicionBtn = document.getElementById("analizarPosicionBtn");
const resultadoJugada = document.getElementById("resultadoJugada");
const analisisJugada = document.getElementById("analisisJugada");
const analisisEvaluacion = document.getElementById("analisisEvaluacion");
const analisisMate = document.getElementById("analisisMate");
const mensajeError = document.getElementById("mensajeError");

function poblarNivelSelect() {
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
        nivelSelect.appendChild(opcion);
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

calcularJugadaBtn.addEventListener("click", calcularJugada);
analizarPosicionBtn.addEventListener("click", analizarPosicion);

poblarNivelSelect();
