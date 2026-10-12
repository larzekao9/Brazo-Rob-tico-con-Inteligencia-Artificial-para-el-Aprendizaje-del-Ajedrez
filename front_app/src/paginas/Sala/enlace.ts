/** Enlace completo para compartir una sala: <origen>/#/sala/K7M2QX. */
export function enlaceDeSala(codigo: string): string {
  return `${window.location.origin}/#/sala/${encodeURIComponent(codigo)}`;
}

/** Normaliza el código escrito por el usuario: sin espacios y en mayúsculas. */
export function normalizarCodigo(texto: string): string {
  return texto.replace(/\s+/g, '').toUpperCase();
}
