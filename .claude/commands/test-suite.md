# /test-suite

Genera una suite de tests completa para un módulo o componente de la plataforma.

## Uso
```
/test-suite <capa> <objetivo>
```
Capas disponibles:
- `backend <app>` — tests Django/DRF para una app (modelos, API, tareas)
- `frontend <componente>` — tests de un componente React con Vitest
- `e2e <flujo>` — test end-to-end de un flujo completo

Ejemplos:
- `/test-suite backend expedientes`
- `/test-suite backend fraud-analysis`
- `/test-suite frontend ExpedientesList`
- `/test-suite e2e registrar-siniestro`

## Qué genera

### Backend (`pytest-django` + `factory_boy`)
- **Factories**: una factory por modelo con datos realistas
- **test_models.py**: validaciones, métodos, señales y constraints
- **test_api.py**: para cada endpoint:
  - Acceso sin autenticación → 401
  - Acceso con rol incorrecto → 403
  - Happy path → 200/201 con datos correctos
  - Validación fallida → 400 con errores descriptivos
  - Aislamiento multi-tenant (un tenant no ve datos de otro)
- **test_tasks.py**: ejecución y resultado de tareas Celery con `task_always_eager`

### Frontend (`Vitest` + `React Testing Library`)
- Render del componente con datos mock
- Estado de carga y estado vacío
- Interacción del usuario (click, input, submit)
- Llamada correcta al hook / API

### E2E (`Playwright` o similar)
- Flujo completo desde login hasta la acción objetivo
- Verificación del estado final en la UI

## Instrucciones
1. Lee el código existente del módulo antes de generar los tests.
2. Usa el agente `backend-django` para tests de backend.
3. Usa el agente `frontend-react` para tests de frontend.
4. Cubre el happy path y al menos 2 casos de error por endpoint.
