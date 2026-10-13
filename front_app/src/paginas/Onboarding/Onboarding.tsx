import {useEffect, useState} from 'react';
import {ArrowRight, Check, ChevronLeft, Sparkles} from 'lucide-react';
import {irA, useRuta} from '../../router';
import {useSesion} from '../../estado/SesionContext';
import {guardarNivelEstimado} from '../../api/backend';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import TableroDemo from '../../componentes/TableroDemo';

const PASOS = [
  {
    id: 'bienvenida',
    titulo: '¡Bienvenido a ChessIA!',
    descripcion: 'Aprende ajedrez con IA, juega contra motores y mejora tu nivel paso a paso.',
    imagen: '♟️',
  },
  {
    id: 'como-jugar',
    titulo: '¿Cómo se juega?',
    descripcion: 'Cada pieza tiene su movimiento único. El rey es la pieza clave: si lo capturan, pierdes.',
    imagen: '♔',
  },
  {
    id: 'nivel',
    titulo: 'Mide tu nivel',
    descripcion: 'Responde unas preguntas rápidas para que empecemos en el nivel justo para ti.',
    imagen: '📊',
  },
];

const PREGUNTAS_NIVEL = [
  {
    id: 1,
    texto: '¿Sabes cómo se mueven todas las piezas?',
    opciones: [
      {valor: 'no', texto: 'No, estoy aprendiendo'},
      {valor: 'basico', texto: 'Sé lo básico'},
      {valor: 'si', texto: 'Sí, las domino'},
    ],
  },
  {
    id: 2,
    texto: '¿Has jugado partidas completas antes?',
    opciones: [
      {valor: 'no', texto: 'Nunca'},
      {valor: 'pocas', texto: 'Algunas (1-10)'},
      {valor: 'muchas', texto: 'Muchas (10+)'},
    ],
  },
  {
    id: 3,
    texto: '¿Conoces conceptos como enroque, jaque mate o tablas?',
    opciones: [
      {valor: 'no', texto: 'No'},
      {valor: 'basico', texto: 'Los he oído'},
      {valor: 'si', texto: 'Sí, los uso'},
    ],
  },
  {
    id: 4,
    texto: '¿Te gustaría aprender tácticas y aperturas?',
    opciones: [
      {valor: 'no', texto: 'Solo lo básico'},
      {valor: 'quizas', texto: 'Me interesa'},
      {valor: 'si', texto: '¡Sí, quiero mejorar!'},
    ],
  },
];

const NIVELES_RESULTADO = {
  Principiante: {nivel: 5, rango: 'Principiante', color: 'primary', icono: Sparkles},
  Intermedio: {nivel: 11, rango: 'Intermedio', color: 'secondary', icono: Check},
  Avanzado: {nivel: 18, rango: 'Avanzado', color: 'tertiary', icono: ArrowRight},
};

export default function Onboarding() {
  const {usuario} = useSesion();
  const {ruta} = useRuta();
  const [pasoActual, setPasoActual] = useState(0);
  const [respuestas, setRespuestas] = useState<Record<number, string>>({});
  const [mostrarResultado, setMostrarResultado] = useState(false);
  const [resultado, setResultado] = useState<{nivel: number; rango: string} | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (usuario?.diagnostico_completado) {
      irA('/inicio');
    }
  }, [usuario, irA]);

  const calcularNivel = () => {
    let puntaje = 0;
    Object.values(respuestas).forEach((r) => {
      if (r === 'no') puntaje += 0;
      else if (r === 'basico' || r === 'pocas' || r === 'quizas') puntaje += 1;
      else puntaje += 2;
    });

    let rango: keyof typeof NIVELES_RESULTADO;
    if (puntaje <= 2) rango = 'Principiante';
    else if (puntaje <= 5) rango = 'Intermedio';
    else rango = 'Avanzado';

    const config = NIVELES_RESULTADO[rango];
    setResultado({nivel: config.nivel, rango});
    setMostrarResultado(true);
  };

  const handleGuardarNivel = async () => {
    if (!resultado) return;
    setGuardando(true);
    try {
      await guardarNivelEstimado(resultado.nivel, resultado.rango);
      irA('/inicio');
    } catch (error) {
      console.error('Error guardando nivel:', error);
      irA('/inicio');
    } finally {
      setGuardando(false);
    }
  };

  const handleSiguiente = () => {
    if (pasoActual < PASOS.length - 1) {
      setPasoActual(pasoActual + 1);
    } else {
      calcularNivel();
    }
  };

  const handleAnterior = () => {
    if (pasoActual > 0) {
      setPasoActual(pasoActual - 1);
      setMostrarResultado(false);
    }
  };

  const handleRespuesta = (preguntaId: number, valor: string) => {
    setRespuestas((prev) => ({...prev, [preguntaId]: valor}));
  };

  if (mostrarResultado && resultado) {
    const config = NIVELES_RESULTADO[resultado.rango as keyof typeof NIVELES_RESULTADO];
    const Icono = config.icono;

    return (
      <div className="flex min-h-dvh flex-col bg-surface-low">
        <header className="flex items-center gap-3 p-4">
          <button onClick={handleAnterior} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
          <h1 className="font-titulo text-xl font-bold text-on-surface">Resultado de tu evaluación</h1>
        </header>

        <main className="flex-1 p-4 space-y-6 overflow-y-auto">
          <GlassCard className="text-center">
            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className={`w-32 h-32 rounded-full bg-${config.color}-container/30`} />
                <div className={`w-24 h-24 rounded-full bg-gradient-to-br from-${config.color} to-${config.color}/60 flex items-center justify-center shadow-lg shadow-${config.color}/40`}>
                  <Icono size={40} className="text-on-primary" />
                </div>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2">
                  <span className={`px-4 py-2 rounded-full bg-${config.color} text-on-primary text-sm font-bold`}>
                    Nivel {resultado.nivel} • {resultado.rango}
                  </span>
                </div>
              </div>
            </div>

            <h2 className="font-titulo text-2xl font-bold text-on-surface mb-2">
              {resultado.rango === 'Principiante' ? '¡Muy bien!' : resultado.rango === 'Intermedio' ? '¡Excelente!' : '¡Impresionante!'}
            </h2>
            <p className="text-on-surface-variant text-center max-w-md mx-auto">
              {resultado.rango === 'Principiante'
                ? 'Estás dando tus primeros pasos en el ajedrez. Has demostrado conocimientos básicos del juego. Con práctica y constancia podrás avanzar al siguiente nivel.'
                : resultado.rango === 'Intermedio'
                ? 'Tienes un buen entendimiento del ajedrez. Conoces aperturas, tácticas básicas y finales elementales. Sigue así para alcanzar nivel avanzado.'
                : 'Demuestras un nivel sólido con buena comprensión posicional y táctica. Estás listo para competir en torneos y seguir perfeccionando tu juego.'}
            </p>
          </GlassCard>

          <GlassCard>
            <h3 className="font-titulo text-lg font-semibold text-on-surface mb-4">Resumen</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-3 rounded-xl bg-primary-container/20">
                <div className="text-2xl font-bold text-primary">{resultado.nivel}</div>
                <div className="text-xs text-on-surface-variant">Nivel asignado</div>
              </div>
              <div className="p-3 rounded-xl bg-secondary-container/20">
                <div className="text-2xl font-bold text-secondary">{Math.max(60, 60 + (resultado.nivel - 5) * 2)}%</div>
                <div className="text-xs text-on-surface-variant">Precisión estimada</div>
              </div>
              <div className="p-3 rounded-xl bg-tertiary-container/20">
                <div className="text-2xl font-bold text-tertiary">4</div>
                <div className="text-xs text-on-surface-variant">Preguntas test</div>
              </div>
            </div>
          </GlassCard>

          <BotonPrimario onClick={handleGuardarNivel} disabled={guardando} className="w-full">
            {guardando ? 'Guardando…' : 'Ir al inicio'}
          </BotonPrimario>
        </main>
      </div>
    );
  }

  const paso = PASOS[pasoActual];
  const esPasoNivel = paso.id === 'nivel';
  const esUltimoPaso = pasoActual === PASOS.length - 1;

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="flex items-center gap-3 p-4">
        {pasoActual > 0 && (
          <button onClick={handleAnterior} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
        )}
        <div className="flex-1">
          <div className="h-1.5 rounded-full bg-outline-variant overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{width: `${((pasoActual + 1) / PASOS.length) * 100}%`}}
            />
          </div>
        </div>
      </header>

      <main className="flex-1 p-4 space-y-6 overflow-y-auto">
        {!esPasoNivel ? (
          <>
            <GlassCard className="text-center py-8">
              <div className="text-6xl mb-4">{paso.imagen}</div>
              <h2 className="font-titulo text-2xl font-bold text-on-surface mb-2">{paso.titulo}</h2>
              <p className="text-on-surface-variant max-w-md mx-auto">{paso.descripcion}</p>
            </GlassCard>

            {paso.id === 'como-jugar' && (
              <GlassCard>
                <h3 className="font-titulo text-lg font-semibold text-on-surface mb-4 text-center">Piezas clave</h3>
                <div className="grid grid-cols-3 gap-3">
                  {['rey', 'dama', 'caballo'].map((tipo) => {
                    const pieza = PIEZAS.find((p) => p.tipo === tipo)!;
                    return (
                      <div key={tipo} className="text-center p-3 rounded-xl bg-surface-container">
                        <img src={`/piezas/w${pieza.letra}.svg`} alt={pieza.nombre} className="w-12 h-12 mx-auto mb-2" />
                        <div className="text-sm font-medium text-on-surface">{pieza.nombre}</div>
                        <div className="text-xs text-on-surface-variant">{pieza.apodo}</div>
                      </div>
                    );
                  })}
                </div>
              </GlassCard>
            )}

            <BotonPrimario onClick={handleSiguiente} className="w-full">
              {esUltimoPaso ? 'Empezar test' : 'Siguiente'}
              <ArrowRight size={16} className="ml-2" />
            </BotonPrimario>
          </>
        ) : (
          <>
            <GlassCard>
              <div className="text-center mb-6">
                <div className="text-5xl mb-2">📊</div>
                <h2 className="font-titulo text-2xl font-bold text-on-surface">Mide tu nivel</h2>
                <p className="text-on-surface-variant">Responde 4 preguntas rápidas para asignarte el nivel inicial.</p>
              </div>

              <div className="space-y-6">
                {PREGUNTAS_NIVEL.map((pregunta) => (
                  <div key={pregunta.id}>
                    <p className="font-medium text-on-surface mb-3">{pregunta.texto}</p>
                    <div className="space-y-2">
                      {pregunta.opciones.map((opcion) => (
                        <button
                          key={opcion.valor}
                          onClick={() => handleRespuesta(pregunta.id, opcion.valor)}
                          className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                            respuestas[pregunta.id] === opcion.valor
                              ? 'border-primary bg-primary-container/20 text-primary'
                              : 'border-outline-variant hover:border-primary/50 text-on-surface'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span>{opcion.texto}</span>
                            {respuestas[pregunta.id] === opcion.valor && <Check size={20} className="text-primary" />}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>

            <BotonPrimario onClick={handleSiguiente} disabled={Object.keys(respuestas).length < PREGUNTAS_NIVEL.length} className="w-full">
              Ver mi nivel
              <ArrowRight size={16} className="ml-2" />
            </BotonPrimario>
          </>
        )}
      </main>
    </div>
  );
}

const PIEZAS = [
  {tipo: 'rey', nombre: 'Rey', letra: 'K', apodo: 'El Monarca'},
  {tipo: 'dama', nombre: 'Dama', letra: 'Q', apodo: 'La Soberana'},
  {tipo: 'caballo', nombre: 'Caballo', letra: 'N', apodo: 'El Infiltrador'},
];