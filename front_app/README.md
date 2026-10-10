# front_app

Web mobile-first para el rol jugador. Mismo backend FastAPI que `frontend/` y `app_movil/`;
mismo stack que `frontend/` (Vite, React 19, TypeScript, Tailwind 4) con el diseño de la app móvil.
Plan completo en `../PLAN_FRONT_APP.md`.

## Levantar

```bash
# terminal 1 - backend (o Docker en :8000)
DATABASE_URL=sqlite:///./test.db KMP_DUPLICATE_LIB_OK=TRUE uvicorn backend.main:app --reload
# terminal 2
cd front_app && npm install && npm run dev      # http://localhost:5174
```

Comprobaciones: `npm run lint` (tsc) y `npm run build`.

## Estructura

- `src/router.ts`: mini-router por hash (`irA`, `useRuta`).
- `src/estado/SesionContext.tsx`: sesión (`useSesion`).
- `src/api/`, `src/dominio/`: copias de la capa de API y utilidades de `frontend/src` (ver cabecera de cada archivo).
- `src/componentes/`: UI compartida (solo la edita el bloque A).
- `src/paginas/`: una carpeta por pantalla.
- Colores y tipografías: solo tokens de `@theme` en `src/index.css`.
