// Copia de frontend/src/contenido/piezas.js (ver PLAN_FRONT_APP.md §2.3).
/**
 * 6 piezas — letra en mayúscula para `rutaImagenPieza` (siempre el set blanco,
 * ilustrativo). `apodo` y `reglaEspecial` son contenido educativo fijo, redactado
 * a mano (no viene de ningún endpoint). `comoSeMueve` describe el movimiento básico
 * y es la base de las tarjetas del onboarding (HU12).
 */
export const PIEZAS = [
  {
    tipo: 'rey',
    nombre: 'Rey',
    articulo: 'el',
    letra: 'K',
    apodo: 'El Monarca',
    comoSeMueve: 'Una casilla en cualquier dirección: arriba, abajo, a los lados o en diagonal.',
    reglaEspecial: 'Se enroca una vez por partida: se pone a resguardo y de paso activa una torre.',
  },
  {
    tipo: 'dama',
    nombre: 'Dama',
    articulo: 'la',
    letra: 'Q',
    apodo: 'La Soberana',
    comoSeMueve: 'En línea recta, por filas, columnas o diagonales, cuantas casillas quiera.',
    reglaEspecial: 'Es la pieza de mayor valor del tablero: se mueve como la torre y el alfil combinados.',
  },
  {
    tipo: 'torre',
    nombre: 'Torre',
    articulo: 'la',
    letra: 'R',
    apodo: 'El Bastión',
    comoSeMueve: 'En línea recta, por filas o columnas, cuantas casillas quiera.',
    reglaEspecial: 'Es la pieza que participa junto al rey en el enroque.',
  },
  {
    tipo: 'alfil',
    nombre: 'Alfil',
    articulo: 'el',
    letra: 'B',
    apodo: 'El Francotirador',
    comoSeMueve: 'En diagonal, cuantas casillas quiera.',
    reglaEspecial: 'Se queda toda la partida en casillas de un mismo color — nunca cambia de color de casilla.',
  },
  {
    tipo: 'caballo',
    nombre: 'Caballo',
    articulo: 'el',
    letra: 'N',
    apodo: 'El Infiltrador',
    comoSeMueve: 'En forma de L: dos casillas en una dirección y una en la otra.',
    reglaEspecial: 'Es la única pieza que puede saltar por encima de otras piezas.',
  },
  {
    tipo: 'peon',
    nombre: 'Peón',
    articulo: 'el',
    letra: 'P',
    apodo: 'La Vanguardia',
    comoSeMueve: 'Avanza una casilla hacia adelante (en su primera jugada puede avanzar dos) y captura en diagonal.',
    reglaEspecial: 'Puede capturar "al paso" y se convierte en otra pieza (corona) al llegar a la última fila.',
  },
];
