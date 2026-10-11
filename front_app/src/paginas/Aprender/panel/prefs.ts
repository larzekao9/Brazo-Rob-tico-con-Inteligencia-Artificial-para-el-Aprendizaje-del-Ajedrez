/** Preferencias del panel de Aprender guardadas en el navegador, por usuario. Si el almacenamiento falla, el estado en memoria sigue sirviendo. */

function leerLista(clave: string): string[] {
  try {
    const crudo = localStorage.getItem(clave);
    const lista: unknown = crudo ? JSON.parse(crudo) : [];
    return Array.isArray(lista) ? lista.filter((x): x is string => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

function guardar(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    /* modo privado o cuota llena: no es crítico */
  }
}

const idUsuario = (id: number | null | undefined) => id ?? 'anon';

/** Piezas que el jugador ya miró en la galería (logro "Conocé las 6 piezas" y capítulo del camino). */
export function cargarPiezasVistas(id: number | null | undefined): string[] {
  return leerLista(`panel_aprendizaje_piezas_${idUsuario(id)}`);
}
export function guardarPiezasVistas(id: number | null | undefined, piezas: string[]): void {
  guardar(`panel_aprendizaje_piezas_${idUsuario(id)}`, JSON.stringify(piezas));
}

/** Capítulos del camino que el propio jugador marcó como vistos (los que no se pueden medir con partidas). */
export function cargarCapitulosVistos(id: number | null | undefined): string[] {
  return leerLista(`camino_capitulos_vistos_${idUsuario(id)}`);
}
export function guardarCapitulosVistos(id: number | null | undefined, ids: string[]): void {
  guardar(`camino_capitulos_vistos_${idUsuario(id)}`, JSON.stringify(ids));
}

/** Preferencia de accesibilidad: texto más grande en las explicaciones. */
export function cargarLecturaFacil(id: number | null | undefined): boolean {
  try {
    return localStorage.getItem(`panel_aprendizaje_lectura_facil_${idUsuario(id)}`) === '1';
  } catch {
    return false;
  }
}
export function guardarLecturaFacil(id: number | null | undefined, activo: boolean): void {
  guardar(`panel_aprendizaje_lectura_facil_${idUsuario(id)}`, activo ? '1' : '0');
}
