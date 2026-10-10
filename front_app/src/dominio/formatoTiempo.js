// Copia de frontend/src/formatoTiempo.js (ver PLAN_FRONT_APP.md §2.3). Mantener alineado con el original.
/**
 * Utilidades puras para mostrar fechas que manda el backend. Sin JSX ni fetch
 * (mismo criterio que ajedrez.js y nivelJugador.js).
 */

/**
 * Convierte un texto ISO del backend en `Date`, o `null` si no se puede leer.
 * El backend trabaja en UTC, pero al pasar por la base de datos una fecha puede
 * llegar sin indicador de zona horaria ("2026-09-28T14:03:11"); el navegador la
 * tomaría como hora local y el "hace X" saldría corrido varias horas, así que en
 * ese caso se interpreta como UTC.
 */
export function fechaDesdeIso(iso) {
  if (typeof iso !== 'string' || iso.trim() === '') return null;
  const texto = iso.trim();
  const tieneZona = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(texto);
  const tieneHora = texto.includes('T');
  const fecha = new Date(tieneZona || !tieneHora ? texto : `${texto}Z`);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

/**
 * Tiempo transcurrido en lenguaje simple: "hace unos segundos", "hace 5 min",
 * "hace 3 h", "hace 2 días". `null` si la fecha no es válida. Una fecha
 * ligeramente en el futuro (relojes desfasados) se muestra como "hace unos segundos".
 */
export function tiempoRelativo(iso, ahora = Date.now()) {
  const fecha = fechaDesdeIso(iso);
  if (!fecha) return null;
  const segundos = Math.max(0, Math.round((ahora - fecha.getTime()) / 1000));
  if (segundos < 45) return 'hace unos segundos';
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.round(horas / 24);
  return `hace ${dias} ${dias === 1 ? 'día' : 'días'}`;
}

/** Fecha y hora locales legibles ("28/09/2026, 14:03"), o el texto original si no se puede leer. */
export function fechaHoraLegible(iso) {
  const fecha = fechaDesdeIso(iso);
  if (!fecha) return typeof iso === 'string' && iso !== '' ? iso : null;
  return fecha.toLocaleString('es-BO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
