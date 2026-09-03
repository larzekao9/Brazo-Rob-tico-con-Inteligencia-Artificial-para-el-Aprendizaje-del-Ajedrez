# /react-component

Genera un componente React con TypeScript + Tailwind + Shadcn/ui para la plataforma de Gestión de Siniestros.

## Uso
```
/react-component <tipo> <nombre>
```
Tipos disponibles:
- `page` — página completa con layout y navegación
- `table` — tabla con paginación, filtros y acciones
- `form` — formulario con React Hook Form + Zod
- `card` — tarjeta de resumen o KPI
- `modal` — diálogo de confirmación o entrada de datos
- `detail` — vista de detalle de una entidad

Ejemplos:
- `/react-component page ExpedientesList`
- `/react-component form CrearExpediente`
- `/react-component table AseguradosTable`

## Qué genera

### Componente principal
- TypeScript estricto, sin `any`
- Props tipadas con `interface`
- Estados de carga, error y vacío manejados
- Responsive con Tailwind (mobile-first)

### Hook de datos (si aplica)
- `use<Nombre>` con TanStack Query
- Mutaciones con `onSuccess` toast y `onError` toast
- Tipos de respuesta de la API definidos

### Validación (si es form)
- Esquema Zod con mensajes de error en español
- Integración con React Hook Form

## Instrucciones
1. Pregunta qué datos muestra o captura el componente.
2. Usa componentes de Shadcn/ui (`Table`, `Dialog`, `Form`, `Card`, etc.).
3. Conecta con el endpoint de la API correspondiente.
4. Maneja los tres roles (Admin/Supervisor/Analista) ocultando acciones no permitidas.
5. Usa el agente `frontend-react` para la implementación.
