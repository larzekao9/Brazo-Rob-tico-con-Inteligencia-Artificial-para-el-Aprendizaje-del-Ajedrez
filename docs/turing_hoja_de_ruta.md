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
| 0 | Interfaz UCI + medición de Elo base contra Stockfish con Elo calibrado | En curso |
| 1 | Búsqueda ligera sobre la red + libro de aperturas | Pendiente |
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

## Ficha del modelo (se completa al cerrar cada versión)

| Versión | Datos | Validación | Top-1 | Notas |
|---|---|---|---|---|
| v1 | 200 partidas | por posición | 12,4 % | Prueba de pipeline |
| v5 | 12.000 partidas, ELO ≥ 2000 | 90/10 por posición (inflada) | 42,1 % | SE-ResNet-8 |
| v6 | 35.000 partidas, ELO ≥ 2200 | por partida entera | 47,6 % (época 9) | Sobreajuste desde la época 9 |

## Límites declarados

- La red sola imita jugadas de maestros pero no busca variantes: pierde contra Stockfish desde el nivel 5.
- "Maestro 18" es una etiqueta de la escala del sistema (ELO de los datos de entrenamiento), no una fuerza medida.
- Las mediciones actuales usan pocas partidas y un solo tiempo de Stockfish; sirven para comparar y ubicar el orden de magnitud.
