import {useEffect, useRef, useState} from 'react';
import {ChevronLeft, Camera, LogOut, User, Mail, Calendar, Shield, Save, Loader2, AlertCircle, CheckCircle, Trophy, Target} from 'lucide-react';
import {irA, useRuta} from '../../router';
import {useSesion} from '../../estado/SesionContext';
import {obtenerPerfil, actualizarPerfil, subirFotoPerfil, guardarNivelEstimado} from '../../api/backend';
import GlassCard from '../../componentes/GlassCard';
import BotonPrimario from '../../componentes/BotonPrimario';
import Cargando from '../../componentes/Cargando';
import ErrorReintentar from '../../componentes/ErrorReintentar';

const NIVELES_DISPONIBLES = [
  {nivel: 5, rango: 'Principiante', color: 'primary', descripcion: 'Estás aprendiendo lo básico'},
  {nivel: 11, rango: 'Intermedio', color: 'secondary', descripcion: 'Conoces tácticas y aperturas'},
  {nivel: 18, rango: 'Avanzado', color: 'tertiary', descripcion: 'Nivel de competición'},
];

export default function Perfil() {
  const {usuario, recargarUsuario, cerrarSesion} = useSesion();
  const {ruta} = useRuta();
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [subiendoFoto, setSubiendoFoto] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [formData, setFormData] = useState({
    nombre: '',
    edad: '',
    descripcion: '',
    nivel_estimado: 0,
    rango_estimado: '',
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const cargar = async () => {
      try {
        const perfil = await obtenerPerfil();
        setFormData({
          nombre: perfil.nombre || '',
          edad: perfil.edad?.toString() || '',
          descripcion: perfil.descripcion || '',
          nivel_estimado: perfil.nivel_estimado || 0,
          rango_estimado: perfil.rango_estimado || '',
        });
      } catch (err) {
        console.error('Error cargando perfil:', err);
        setError('No se pudo cargar el perfil');
      } finally {
        setCargando(false);
      }
    };
    cargar();
  }, []);

  const handleChange = (campo: string, valor: any) => {
    setFormData((prev) => ({...prev, [campo]: valor}));
    setError(null);
    setExito(null);
  };

  const handleGuardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      await actualizarPerfil({
        nombre: formData.nombre.trim(),
        edad: formData.edad ? parseInt(formData.edad) : null,
        descripcion: formData.descripcion.trim() || null,
      });
      await recargarUsuario();
      setEditando(false);
      setExito('Perfil actualizado correctamente');
      setTimeout(() => setExito(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Error actualizando perfil');
    } finally {
      setGuardando(false);
    }
  };

  const handleCambiarNivel = async (nivel: number, rango: string) => {
    setGuardando(true);
    try {
      await guardarNivelEstimado(nivel, rango);
      await recargarUsuario();
      setFormData((prev) => ({...prev, nivel_estimado: nivel, rango_estimado: rango}));
      setExito(`Nivel cambiado a ${rango} (${nivel})`);
      setTimeout(() => setExito(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Error cambiando nivel');
    } finally {
      setGuardando(false);
    }
  };

  const handleSeleccionarFoto = () => fileInputRef.current?.click();

  const handleSubirFoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0];
    if (!archivo) return;

    if (!archivo.type.startsWith('image/')) {
      setError('El archivo debe ser una imagen');
      return;
    }
    if (archivo.size > 5 * 1024 * 1024) {
      setError('La imagen no puede superar 5 MB');
      return;
    }

    setSubiendoFoto(true);
    setError(null);
    try {
      await subirFotoPerfil(archivo);
      await recargarUsuario();
      setExito('Foto actualizada correctamente');
      setTimeout(() => setExito(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Error subiendo foto');
    } finally {
      setSubiendoFoto(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleCerrarSesion = () => {
    if (window.confirm('¿Cerrar sesión?')) {
      cerrarSesion();
      irA('/login');
    }
  };

  const getRangoColor = (rango: string) => {
    switch (rango) {
      case 'Principiante': return 'primary';
      case 'Intermedio': return 'secondary';
      case 'Avanzado': return 'tertiary';
      default: return 'primary';
    }
  };

  const handleVolver = () => irA('/inicio');

  if (cargando) {
    return (
      <div className="flex min-h-dvh flex-col bg-surface-low">
        <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur-md border-b border-outline-variant px-4 py-3">
          <div className="flex items-center justify-between">
            <button onClick={handleVolver} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
              <ChevronLeft size={24} />
            </button>
            <div className="flex-1 text-center">
              <p className="text-xs font-medium text-primary tracking-wide">INICIO</p>
              <h1 className="font-titulo text-xl font-bold text-on-surface">Mi Perfil</h1>
            </div>
            <div className="w-10" />
          </div>
        </header>
        <main className="flex-1 flex items-center justify-center">
          <Cargando mensaje="Cargando perfil…" />
        </main>
      </div>
    );
  }

  const rangoActual = formData.rango_estimado || usuario?.rango_estimado || 'Principiante';
  const nivelActual = formData.nivel_estimado || usuario?.nivel_estimado || 1;
  const colorRango = getRangoColor(rangoActual);

  return (
    <div className="flex min-h-dvh flex-col bg-surface-low">
      <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur-md border-b border-outline-variant px-4 py-3">
        <div className="flex items-center justify-between">
          <button onClick={handleVolver} className="p-2 rounded-full hover:bg-surface-container" aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
          <div className="flex-1 text-center">
            <p className="text-xs font-medium text-primary tracking-wide">INICIO</p>
            <h1 className="font-titulo text-xl font-bold text-on-surface">Mi Perfil</h1>
          </div>
          <div className="w-10" />
        </div>
      </header>

      <main className="flex-1 p-4 space-y-4 overflow-y-auto pb-24">
        {error && (
          <div className="fixed top-4 left-4 right-4 z-50 max-w-md mx-auto animate-slide-down">
            <GlassCard className="bg-error-container border-error/30">
              <div className="flex items-center gap-2">
                <AlertCircle size={20} className="text-error" />
                <span className="text-on-error-container text-sm">{error}</span>
              </div>
            </GlassCard>
          </div>
        )}

        {exito && (
          <div className="fixed top-4 left-4 right-4 z-50 max-w-md mx-auto animate-slide-down">
            <GlassCard className="bg-primary-container border-primary/30">
              <div className="flex items-center gap-2">
                <CheckCircle size={20} className="text-primary" />
                <span className="text-on-primary-container text-sm">{exito}</span>
              </div>
            </GlassCard>
          </div>
        )}

        <GlassCard>
          <div className="flex items-center gap-4">
            <div className="relative">
              {usuario?.avatar_url ? (
                <img
                  src={usuario.avatar_url}
                  alt={usuario.nombre}
                  className="w-24 h-24 rounded-2xl object-cover border-4 border-primary/20"
                />
              ) : (
                <div className="w-24 h-24 rounded-2xl bg-primary-container/30 flex items-center justify-center border-4 border-primary/20">
                  <User size={40} className="text-primary" />
                </div>
              )}
              <button
                onClick={handleSeleccionarFoto}
                disabled={subiendoFoto}
                className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center shadow-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                aria-label="Cambiar foto de perfil"
              >
                {subiendoFoto ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Camera size={18} />
                )}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleSubirFoto}
                className="hidden"
              />
            </div>

            <div className="flex-1 min-w-0">
              {editando ? (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={formData.nombre}
                    onChange={(e) => handleChange('nombre', e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface-container text-on-surface text-lg font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Tu nombre"
                  />
                  <div className="flex gap-3">
                    <input
                      type="number"
                      value={formData.edad}
                      onChange={(e) => handleChange('edad', e.target.value)}
                      min="5"
                      max="100"
                      placeholder="Edad"
                      className="w-24 px-3 py-2 rounded-lg bg-surface-container text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <select
                      value={formData.rango_estimado}
                      onChange={(e) => handleChange('rango_estimado', e.target.value)}
                      className="flex-1 px-3 py-2 rounded-lg bg-surface-container text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      {NIVELES_DISPONIBLES.map((n) => (
                        <option key={n.rango} value={n.rango}>
                          {n.rango} (Nivel {n.nivel})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ) : (
                <div>
                  <h2 className="font-titulo text-xl font-bold text-on-surface truncate">{formData.nombre || usuario?.nombre || 'Jugador'}</h2>
                  <div className="flex items-center gap-3 mt-1 text-sm text-on-surface-variant">
                    <span className="flex items-center gap-1">
                      <Mail size={14} />
                      {usuario?.email}
                    </span>
                    {formData.edad && (
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {formData.edad} años
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium bg-${colorRango}-container text-${colorRango}`}>
                      {rangoActual} • Nivel {nivelActual}
                    </span>
                    <Shield size={14} className="text-primary" />
                    <span className="text-xs text-primary font-medium">Solo jugadores</span>
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => setEditando(!editando)}
              disabled={guardando}
              className="px-4 py-2 rounded-lg bg-surface-container text-on-surface font-medium hover:bg-surface-container/80 disabled:opacity-50 transition-colors"
            >
              {editando ? (guardando ? 'Guardando…' : 'Guardar') : 'Editar'}
            </button>
          </div>

          {editando && (
            <div className="mt-4 pt-4 border-t border-outline-variant space-y-3">
              <textarea
                value={formData.descripcion}
                onChange={(e) => handleChange('descripcion', e.target.value)}
                placeholder="Cuéntanos algo sobre ti…"
                rows={3}
                className="w-full px-3 py-2 rounded-lg bg-surface-container text-on-surface placeholder-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
              <div className="flex gap-3">
                <button
                  onClick={handleGuardar}
                  disabled={guardando}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-primary text-on-primary font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {guardando ? <Loader2 size={18} className="animate-spin mx-auto" /> : 'Guardar cambios'}
                </button>
                <button
                  onClick={() => setEditando(false)}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-surface-container text-on-surface font-medium hover:bg-surface-container/80 transition-colors"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </GlassCard>

        <GlassCard>
          <h3 className="font-titulo font-semibold text-on-surface mb-4">Tu nivel actual</h3>
          <div className="space-y-3">
            {NIVELES_DISPONIBLES.map((nivel) => (
              <button
                key={nivel.rango}
                onClick={() => handleCambiarNivel(nivel.nivel, nivel.rango)}
                disabled={guardando || (nivel.nivel === nivelActual && nivel.rango === rangoActual)}
                className={`w-full p-4 rounded-xl text-left transition-all ${
                  nivel.nivel === nivelActual && nivel.rango === rangoActual
                    ? `ring-2 ring-${nivel.color} bg-${nivel.color}-container/20`
                    : 'bg-surface-container hover:bg-surface-container/80'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-${nivel.color}-container/30 flex items-center justify-center`}>
                    {nivel.rango === 'Principiante' && <Trophy size={24} className={`text-${nivel.color}`} />}
                    {nivel.rango === 'Intermedio' && <Target size={24} className={`text-${nivel.color}`} />}
                    {nivel.rango === 'Avanzado' && <Shield size={24} className={`text-${nivel.color}`} />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-titulo font-semibold text-on-surface">{nivel.rango}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium bg-${nivel.color}-container text-${nivel.color}`}>
                        Nivel {nivel.nivel}
                      </span>
                      {nivel.nivel === nivelActual && nivel.rango === rangoActual && (
                        <CheckCircle size={16} className={`text-${nivel.color}`} />
                      )}
                    </div>
                    <p className="text-on-surface-variant text-sm mt-1">{nivel.descripcion}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="bg-error-container/10 border-error/20">
          <button
            onClick={handleCerrarSesion}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg text-error font-medium hover:bg-error-container/30 transition-colors"
          >
            <LogOut size={20} />
            <span>Cerrar sesión</span>
          </button>
        </GlassCard>
      </main>
    </div>
  );
}