# Plan: Frontend Razonamiento Neuronal — Implementación por Fases

**Objetivo**: Conectar `RazonamientoNeuronal.jsx` a los endpoints reales del backend (`/aprendizaje/estado-modelo`, `/aprendizaje/inferencia`).

---

## Agente responsable

| Agente | Dominio |
|--------|---------|
| `frontend-react` | Frontend React + API client |

---

## Fases

### ✅ FASE 1 — API Client (`frontend/src/api/backend.js`)
Agregar dos funciones:
```javascript
export async function estadoModelo() {
  // GET /aprendizaje/estado-modelo
}

export async function inferenciaModelo(fen) {
  // POST /aprendizaje/inferencia {fen}
}
```
Mismo estilo que `analizarPosicion`/`calcularJugada` existentes. Propagar errores tal cual (503 → catch en componente).

---

### ✅ FASE 2 — Componente Principal (`RazonamientoNeuronal.jsx`)
Reescribir adoptando paleta/tipografía de `DESIGN.md` (tokens ya en `index.css` Tailwind v4).

**Cambios clave:**
1. **Selector de posición**: reusar `listarPartidas`/`obtenerPartida` (como `Aprendizaje.jsx`) en vez de FEN fijo
2. **Tablero 8×8**: usar utilidades de `frontend/src/ajedrez.js` (`fenAMatriz`, `rutaImagenPieza`, `piezaEnCasilla`) — no duplicar lógica
3. **Candidatas**: `inferenciaModelo(fen).candidatas` (probabilidad real del modelo)
4. **Diagnóstico Pedagógico**: reusar `clasificarJugada`/`caidaDeJugada` de `frontend/src/aprendizaje.js` (mismas funciones que `Aprendizaje.jsx` para HU5) sobre comparación modelo-vs-Stockfish
5. **Mapa de calor 8×8 ("Mapa de Activación")**: pintar con `saliencia` real (64 floats) en vez de clases Tailwind fijas
6. **Telemetría superior**: latencia = medida real del último request; reemplazar "VRAM/GPU RTX A6000" fijos por `estadoModelo().dispositivo` real
6. **Estado sin checkpoint**: si `disponible===false` o 503 → mensaje claro ("Modelo no disponible en este entorno — falta el checkpoint local")

---

### ✅ FASE 3 — Partes decorativas (conservar visualmente + rotular)
Lo que **no** puede ser real por arquitectura del modelo actual (CNN 3 bloques, sin atención ni MCTS):
- "Atención Multi-Cabezal (8 heads)" 
- "Monte Carlo Tree Search"
- Morfología cortical 3D / hemisferios / fisura

**Acción**: conservar visualmente del diseño aprobado, pero envolver con `AvisoVistaPrevia` existente:
```jsx
<AvisoVistaPrevia 
  hu="Módulo 5 · HU6 ampliada"
  descripcionCorta="Candidatas, saliencia, comparación Stockfish y estado del modelo son reales; el resto del grafo (atención multi-cabezal, MCTS, morfología 3D) es diagrama conceptual"
/>
```
Mismo patrón que ya usa el resto del proyecto.

---

## Archivos a tocar

| Archivo | Qué cambia |
|---------|------------|
| `frontend/src/api/backend.js` | + `estadoModelo()`, `inferenciaModelo(fen)` |
| `frontend/src/paginas/RazonamientoNeuronal/RazonamientoNeuronal.jsx` | Reescritura completa conectada a API real |
| (posible) `frontend/src/aprendizaje.js` | Verificar que `clasificarJugada`/`caidaDeJugada` exportadas y reutilizables |

---

## Verificación

1. Levantar backend (`uvicorn backend.main:app --reload`)
2. Levantar frontend (`cd frontend && npm run dev`)
3. Navegar a `/razonamiento-neuronal`
4. Verificar:
   - Selector de partida carga FEN reales
   - Tablero renderiza desde FEN
   - Click "Disparar Pulso" / auto-inferencia → muestra candidatas con probs reales
   - Heatmap 8×8 refleja `saliencia` real
   - Diagnóstico pedagógico usa lógica compartida con `Aprendizaje.jsx`
   - Telemetría muestra latencia real + dispositivo real
   - Sin checkpoint local → mensaje claro, no roto
   - Partes decorativas rotuladas con `AvisoVistaPrevia`