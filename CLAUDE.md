# CLAUDE.md

Instrucciones de proyecto para Claude Code. Este archivo se lee automáticamente al abrir
la carpeta del repositorio.

**Contexto completo del proyecto y plan semana a semana:** ver `PLAN_IMPLEMENTACION.md` en la
raíz del repo. Este archivo (`CLAUDE.md`) define reglas de comportamiento; `PLAN_IMPLEMENTACION.md`
define qué construir y en qué orden.

---

## Quién sos en este proyecto

Estás ayudando a implementar el sistema descrito en `PLAN_IMPLEMENTACION.md`: un brazo robótico
potenciado con inteligencia artificial para el aprendizaje del ajedrez. El equipo es Suárez Burgos
Hebert y Arce Kao Luis Ángel, estudiantes de Ingeniería Informática (UAGRM). Es un proyecto
académico con fecha de defensa próxima — priorizá siempre lo que se pueda demostrar funcionando
por sobre lo que sea técnicamente más elegante pero arriesgado de terminar a tiempo.

---

## Reglas técnicas obligatorias (no renegociables sin avisar)

Estas decisiones ya están tomadas y documentadas en el PAPs del proyecto. No las cuestiones ni
las cambies por tu cuenta — si creés que alguna no es viable, decilo explícitamente y esperá
confirmación antes de desviarte.

1. **Stockfish es siempre la fuente de la jugada real.** El modelo de aprendizaje propio predice
   y explica al estilo humano, pero nunca reemplaza a Stockfish como quien decide qué jugada se
   ejecuta.
2. **Nunca implementar aprendizaje "en vivo" durante una partida en curso.** El modelo solo se
   reentrena en lotes controlados y versionados, después de acumular partidas, nunca de forma
   directa mientras el sistema está en uso.
3. **No tocar el brazo físico real todavía.** Todo lo que sea ejecución del brazo se hace contra
   el simulador (PyBullet). La integración con hardware real depende de la llegada del kit
   importado y es una fase posterior, fuera de este plan de 3 semanas.
4. **Fijar versiones exactas en `requirements.txt`** para toda librería nueva que agregues
   (`python-chess`, `stockfish`, `opencv-python`, `pybullet`, `fastapi`, `torch`, etc.). Nunca
   dejar una dependencia sin versión fijada.
5. **Seguir la estructura de carpetas** ya definida en `PLAN_IMPLEMENTACION.md` (`backend/`,
   `training/`, `frontend/`, `docs/`). Si hace falta una carpeta nueva, proponela antes de crearla
   por tu cuenta si cambia la estructura general.

---

## Qué SÍ debés hacer

- Seguir el orden de `PLAN_IMPLEMENTACION.md` (motor de ajedrez antes que visión; visión antes
  que integración completa) — el orden no es arbitrario, cada paso da algo demostrable antes de
  depender del siguiente.
- Escribir funciones chicas y probables de forma aislada (por ejemplo, `calcular_jugada(fen, nivel)`
  debe poder probarse sin cámara ni modelo entrenado).
- Agregar un test básico por cada módulo nuevo, aunque sea simple.
- Documentar con docstrings las funciones públicas de cada módulo.
- Avisar explícitamente si un paso del plan no es viable en el tiempo disponible, y proponer una
  alternativa acotada, en vez de forzar una implementación a medias.
- Preguntar antes de introducir una librería o herramienta que no esté ya en la lista del stack
  tecnológico del proyecto.

## Qué NO debés hacer

- No commitear datasets completos ni checkpoints de modelos pesados directamente al repositorio.
  Esos archivos van a `.gitignore`; el dataset se referencia por su fuente (Lichess) y los
  checkpoints se guardan en Google Drive (ver sección de Colab en `PLAN_IMPLEMENTACION.md`).
- No incluir credenciales, tokens ni claves de API en ningún archivo del repositorio, ni siquiera
  en archivos de configuración de ejemplo.
- No agregar funcionalidad fuera del alcance de las 3 semanas (ver "Qué NO hacer" al final de
  `PLAN_IMPLEMENTACION.md`) sin que te lo pidan explícitamente.
- No optimizar prematuramente el modelo de aprendizaje antes de tener el pipeline funcionando
  de punta a punta.

---

## Reglas de Git y control de versiones — OBLIGATORIO

**Ningún commit, mensaje de pull request, comentario de código, nombre de archivo, ni ningún otro
contenido del repositorio debe mencionar a Claude, Claude Code, Anthropic, ni identificarte como
coautor o colaborador.** El repositorio debe verse como si todo el código lo hubieran escrito
Suárez Burgos Hebert y Arce Kao Luis Ángel directamente.

Concretamente:

- **Nunca agregues la línea `Co-Authored-By: Claude`** ni ninguna variante, en ningún commit.
- **Nunca agregues `🤖 Generated with Claude Code`** ni ningún pie de página similar al mensaje
  de commit o a la descripción de un pull request.
- **Nunca uses tu propio nombre o el de Anthropic** como autor o committer de git. El autor del
  commit siempre debe ser la persona que está usando la sesión (configurado en su `git config
  user.name` / `user.email` local).
- Los mensajes de commit deben ser simples, en español o inglés según el resto del repo, y
  describir solo el cambio de código — sin mencionar que fueron asistidos por IA.
- Esta regla se aplica también a comentarios dentro del código, nombres de variables, archivos
  de documentación generados, y cualquier otro artefacto que termine en el repositorio.

Esta regla ya está reforzada a nivel de configuración en `.claude/settings.json` (ver ese archivo
en la raíz del repo) — pero seguí esta instrucción explícitamente de todas formas, incluso si por
algún motivo la configuración no se aplicara en tu entorno.

---

## Cuando algo no esté claro

Si un paso del plan es ambiguo o falta información para decidir (por ejemplo, qué arquitectura
exacta de CNN usar, o qué formato de imagen esperar de la cámara), elegí la opción más simple y
razonable, documentá brevemente por qué la elegiste, y seguí avanzando — no te quedes esperando
confirmación para decisiones chicas. Reservá las preguntas para decisiones que cambien la
arquitectura general o que contradigan una de las reglas técnicas obligatorias de arriba.
