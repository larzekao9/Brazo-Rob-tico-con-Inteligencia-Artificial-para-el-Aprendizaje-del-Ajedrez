# Turing: hoja de ruta hacia un motor propio, medido y reutilizable

**Objetivo (Expociencia):** presentar a Turing como un motor de ajedrez propio que decide por sí solo, juega como un
maestro humano, es explicable y tiene su **fuerza medida y versionada**. No se promete igualar a Stockfish (años de
desarrollo, millones de posiciones por segundo); se promete **un número real** y una curva de mejora comprobable.

**Reglas que no cambian** (`CLAUDE.md`): Turing decide sin Stockfish al jugar; Stockfish solo mide (rival de
comparación) y puede dar etiquetas durante el entrenamiento; nada de aprendizaje en vivo (solo lotes versionados);
los checkpoints no se suben a git.

## Estado

| # | Paso | Estado |
|---|---|---|
| 0 | Interfaz UCI + medición de Elo base contra Stockfish con Elo calibrado | **Hecho** (v6 ≈ 1355 Elo) |
| 1 | Búsqueda ligera sobre la red + libro de aperturas | Búsqueda **hecha y medida**: 92,5 % contra la red sola y **Elo ≈ 1808** (profundidad 3, peso 40). Falta integrarla a la app/UCI y el libro de aperturas |
| 2 | Bot de Lichess (rating público) | Pendiente |
| 3 | Cabeza de valor + búsqueda estilo AlphaZero (datos: base de evaluaciones de Lichess) | Pendiente |
| 4 | Evolución visible: gráfico de Elo por versión + modo "escalera" | Pendiente |
| 5 | Ficha del modelo y documentación | Continuo (este archivo) |

## Cómo se trabaja (sesiones de duración impredecible)

Cada pieza termina en un estado **medido y commiteado**, nunca a medias. Lo largo (entrenar, 200+ partidas de medición)
corre en segundo plano o en Colab con reanudación, así una noche entera rinde.

| Tiempo disponible | Qué entra |
|---|---|
| **1 a 2 horas** | Una pieza chica: p. ej. un mejoramiento de la búsqueda y su medición corta, un test, un apartado de documentación |
| **Una tarde (3 a 5 h)** | Un paso completo: UCI + medición base, o la búsqueda ligera con su comparación contra la versión anterior |
| **Toda la noche** | Lo largo en segundo plano: preparar datos y entrenar en Colab, o 200 a 400 partidas de medición |

**Criterio para aceptar cualquier mejora:** se mide con `training/enfrentar_modelos.py` contra la versión anterior y contra
Stockfish; solo se acepta si el puntaje sube de forma clara (intervalo de confianza que no incluya el empate). Si no, se
descarta o se revierte.

## Registro de mediciones

| Fecha | Versión / cambio | Medición | Resultado |
|---|---|---|---|
| 2026-10-13 | v6 contra v5 | 40 partidas, 20 aperturas, ambos colores | +23 =15 −2 (76,2 %, ≈ +200 Elo) |
| 2026-10-13 | v6 contra Stockfish nivel 0 | 12 partidas a 0,05 s | 50 % |
| 2026-10-13 | v6 contra Stockfish niveles 3 / 5 | 12 partidas c/u | 20,8 % / 4,2 % |
| 2026-10-13 | v6 contra Stockfish niveles 8 a 20 | 20 partidas c/u | ≈ 0 % |
| 2026-10-13 | **v6, Elo base** (`training/medir_elo.py`, Stockfish con `UCI_Elo`, 0,2 s por jugada, 40 partidas por rival) | 1320: +16 =9 −15 (51,2 %); 1500: +7 =10 −23 (30,0 %); 1700: +2 =9 −29 (16,2 %) | **Elo estimado 1355** (intervalo ~95 %: 1284 a 1427; 120 partidas) |

Búsqueda de variantes sobre la v6 (red + cálculo contra la **misma red sola**, 40 partidas, 20 aperturas, máx. 1 s por jugada de búsqueda):

| Fecha | Profundidad / peso de la red | Resultado (+ = −) | Puntaje | Dif. Elo (IC 95 %) |
|---|---|---|---|---|
| 2026-10-14 | 2 / 40 | +29 =11 −0 | 86,2 % | +319 (+234 a +454) |
| 2026-10-14 | 3 / 20 | +29 =9 −2 | 83,8 % | +285 (+191 a +437) |
| 2026-10-14 | **3 / 40** | **+34 =6 −0** | **92,5 %** | **+436 (+330 a +679)** |
| 2026-10-14 | 3 / 100 | +24 =15 −1 | 78,8 % | +228 (+150 a +333) |

**Elo absoluto de la v6 con búsqueda** (profundidad 3, peso de la red 40, 1 s máx. de búsqueda por jugada; Stockfish con `UCI_Elo`, 0,2 s por jugada, 40 partidas por rival, 2026-10-14):

| Rival | Resultado (G/E/P) | Puntaje | Red sola (mismo rival) |
|---|---|---|---|
| 1500 | +30 =7 −3 | 83,8 % | 30,0 % |
| 1700 | +20 =4 −16 | 55,0 % | 16,2 % |
| 1900 | +11 =17 −12 | 48,8 % | — |

**Elo estimado: 1808** (intervalo ~95 %: 1737 a 1878; 120 partidas), contra **1355** de la red sola: la búsqueda aporta unos **+450 Elo** en esta escala. Sigue siendo relativo a este rival y a 0,2 s por jugada. (La primera corrida se cayó por un `TimeoutError` de Stockfish en el rival 1700; el rival 1500 ya estaba medido y se repitió solo 1700 y 1900. `JugadorStockfish` ahora reinicia el motor y reintenta.)

## Ficha del modelo (se completa al cerrar cada versión)

| Versión | Datos | Validación | Top-1 | Notas |
|---|---|---|---|---|
| v1 | 200 partidas | por posición | 12,4 % | Prueba de pipeline |
| v5 | 12.000 partidas, ELO ≥ 2000 | 90/10 por posición (inflada) | 42,1 % | SE-ResNet-8 |
| v6 | 35.000 partidas, ELO ≥ 2200 | por partida entera | 47,6 % (época 9) | Sobreajuste desde la época 9 |

## Cómo reproducir las mediciones

- Elo base: `python -m training.medir_elo --checkpoint <modelo.pt> --elos 1320 1500 1700 --aperturas 20 --tiempo 0.2`
- Una versión contra otra y contra la escala de Stockfish: `python -m training.enfrentar_modelos --a <anterior.pt> --b <nueva.pt>`
- Turing como motor UCI (para cualquier programa de ajedrez): `training/turing_uci.bat` o `python -m training.turing_uci`

## Límites declarados

- La red sola imita jugadas de maestros pero no busca variantes: pierde contra Stockfish desde el nivel 5.
- "Maestro 18" es una etiqueta de la escala del sistema (ELO de los datos de entrenamiento), no una fuerza medida.
- Las mediciones actuales usan pocas partidas y un solo tiempo de Stockfish; sirven para comparar y ubicar el orden de magnitud.
- El Elo de Stockfish (`UCI_Elo`) está calibrado para tiempos largos; a 0,2 s por jugada no es exacto, así que el 1355 es **relativo a ese rival y ese tiempo**, no un Elo oficial. Sirve para comparar versiones (v6 contra v7, con la búsqueda, etc.).
