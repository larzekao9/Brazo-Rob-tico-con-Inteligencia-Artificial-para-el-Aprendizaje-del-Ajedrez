import {useCallback, useEffect, useState} from 'react';

/** Quita el formato Markdown y los símbolos para que la voz no diga "asterisco" o "almohadilla". */
export function limpiarTextoParaVoz(texto: string | null | undefined): string {
  if (!texto) return '';
  return texto
    .replace(/```[\s\S]*?```/g, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^\s*>\s+/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[*_~`#|]/g, '')
    .replace(/([.!?;:])\s*\n+/g, '$1 ')
    .replace(/\n+/g, '. ')
    .replace(/\.{2,}/g, '.')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

export interface Narracion {
  narrar(texto: string): void;
  detener(): void;
  /** Refleja el estado real del motor de voz (eventos start/end/error), no un booleano optimista. */
  narrando: boolean;
  disponible: boolean;
}

/**
 * Narración con la Web Speech API nativa (`speechSynthesis`), sin dependencias.
 * Una sola instancia por pantalla: dos lectores a la vez se pisan entre sí.
 */
export function useNarracion(): Narracion {
  const disponible = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const [narrando, setNarrando] = useState(false);

  const narrar = useCallback(
    (texto: string) => {
      if (!disponible) return;
      const limpio = limpiarTextoParaVoz(texto);
      if (!limpio) return;
      window.speechSynthesis.cancel();
      const frase = new SpeechSynthesisUtterance(limpio);
      frase.lang = 'es-ES';
      frase.onstart = () => setNarrando(true);
      frase.onend = () => setNarrando(false);
      frase.onerror = () => setNarrando(false);
      window.speechSynthesis.speak(frase);
    },
    [disponible],
  );

  const detener = useCallback(() => {
    if (!disponible) return;
    window.speechSynthesis.cancel();
    setNarrando(false);
  }, [disponible]);

  useEffect(
    () => () => {
      if (disponible) window.speechSynthesis.cancel();
    },
    [disponible],
  );

  return {narrar, detener, narrando, disponible};
}
