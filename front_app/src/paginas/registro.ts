import type {ComponentType} from 'react';
import type {RutaApp} from '../router';
import Login from './Login/Login';
import Onboarding from './Onboarding/Onboarding';
import Inicio from './Inicio/Inicio';
import SeleccionModo from './Jugar/SeleccionModo';
import Configuracion from './Jugar/Configuracion';
import Partida from './Jugar/Partida';
import Resultado from './Jugar/Resultado';
import Camino from './Aprender/Camino';
import Piezas from './Aprender/Piezas';
import Tablero from './Aprender/Tablero';
import FilasColumnas from './Aprender/FilasColumnas';
import PosicionInicial from './Aprender/PosicionInicial';
import Tutor from './Aprender/Tutor';
import Historial from './Historial/Historial';
import Perfil from './Perfil/Perfil';
import Demostracion from './Demostracion/Demostracion';

/** Qué componente pinta cada ruta. Cada página exporta un componente por defecto sin props. */
export const PAGINAS: Record<RutaApp, ComponentType> = {
  '/login': Login,
  '/onboarding': Onboarding,
  '/inicio': Inicio,
  '/jugar': SeleccionModo,
  '/jugar/config': Configuracion,
  '/jugar/partida/:id': Partida,
  '/jugar/resultado/:id': Resultado,
  '/aprender': Camino,
  '/aprender/piezas': Piezas,
  '/aprender/tablero': Tablero,
  '/aprender/filas-columnas': FilasColumnas,
  '/aprender/posicion-inicial': PosicionInicial,
  '/aprender/tutor': Tutor,
  '/historial': Historial,
  '/perfil': Perfil,
  '/demostracion': Demostracion,
};
