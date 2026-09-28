-- =====================================================================
-- BASE COMPLETA (desarrollo local) - Sistema Tutor Inteligente de Ajedrez
-- PostgreSQL 16. Generado desde backend/modelos/tablas_orm.py con
-- docs/base_de_datos/generar_esquema.py. No editar a mano: cambiar el modelo y
-- volver a generar.
--
-- La aplicación crea estas tablas sola al arrancar (backend/database.py,
-- crear_tablas) y siembra los usuarios de prueba de docs/usuarios_locales_dev.md.
-- Este script sirve para crear la misma base por fuera de la aplicación:
--
--     CREATE DATABASE ajedrez;              -- una sola vez, conectado a 'postgres'
--     psql -U <usuario> -d ajedrez -f docs/base_de_datos/base_completa.sql
--
-- Para producción en Supabase usar base_supabase_produccion.sql.
-- =====================================================================

-- participante: Estudiantes de un curso, para sesiones del facilitador.
CREATE TABLE participante (
	id SERIAL NOT NULL, 
	nombre VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

-- sesion: Sesión de clase que abre un facilitador, con su dificultad y tipo de oponente.
CREATE TABLE sesion (
	id SERIAL NOT NULL, 
	facilitador VARCHAR, 
	fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	dificultad INTEGER, 
	tipo_oponente VARCHAR, 
	PRIMARY KEY (id)
);

-- usuario: Personas que usan el sistema, con su rol, su nivel de juego y su perfil.
CREATE TABLE usuario (
	id SERIAL NOT NULL, 
	email VARCHAR NOT NULL, 
	nombre VARCHAR NOT NULL, 
	password_hash VARCHAR, 
	rol VARCHAR DEFAULT 'jugador' NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	activo BOOLEAN NOT NULL, 
	google_id VARCHAR, 
	avatar_url VARCHAR, 
	nivel_estimado INTEGER, 
	rango_estimado VARCHAR, 
	edad INTEGER, 
	descripcion VARCHAR, 
	preset_ensenanza VARCHAR, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_usuario_email ON usuario (email);
CREATE INDEX ix_usuario_google_id ON usuario (google_id);

-- calibracion: Una fila por partida terminada que sirvió para medir el nivel del jugador. Con las últimas tres se calcula su nivel vigente.
CREATE TABLE calibracion (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	partida_id VARCHAR NOT NULL, 
	precision_global FLOAT NOT NULL, 
	nivel_partida INTEGER NOT NULL, 
	rango_partida VARCHAR NOT NULL, 
	total_jugadas INTEGER NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_calibracion_usuario_partida UNIQUE (usuario_id, partida_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id)
);
CREATE INDEX ix_calibracion_usuario_id ON calibracion (usuario_id);

-- exportacion_dataset: Una fila por cada vez que un facilitador descargó el dataset de partidas para reentrenar el modelo propio (HU4, todavía pendiente de construir).
CREATE TABLE exportacion_dataset (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	corte_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	cantidad_partidas INTEGER NOT NULL, 
	cantidad_jugadas INTEGER NOT NULL, 
	formato VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id)
);
CREATE INDEX ix_exportacion_dataset_usuario_id ON exportacion_dataset (usuario_id);

-- mensaje_tutor: Historial de la conversación de cada jugador con el tutor Turing (memoria multi-turno).
CREATE TABLE mensaje_tutor (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	rol VARCHAR NOT NULL, 
	contenido VARCHAR NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id)
);
CREATE INDEX ix_mensaje_tutor_usuario_id ON mensaje_tutor (usuario_id);

-- partida: Cada partida jugada: quién la jugó, contra qué oponente, a qué nivel, la posición actual y las funciones opcionales que el facilitador habilitó.
CREATE TABLE partida (
	id VARCHAR NOT NULL, 
	usuario_id INTEGER, 
	participante_id INTEGER, 
	sesion_id INTEGER, 
	fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	resultado VARCHAR, 
	tipo VARCHAR NOT NULL, 
	fen VARCHAR NOT NULL, 
	fen_inicial VARCHAR, 
	nivel INTEGER NOT NULL, 
	tipo_oponente VARCHAR NOT NULL, 
	jugadas_uci VARCHAR NOT NULL, 
	permite_simulacion_3d BOOLEAN DEFAULT 'false' NOT NULL, 
	permite_camara BOOLEAN DEFAULT 'false' NOT NULL, 
	es_demostracion BOOLEAN DEFAULT 'false' NOT NULL, 
	usa_brazo BOOLEAN DEFAULT 'false' NOT NULL, 
	estado VARCHAR DEFAULT 'en_curso' NOT NULL, 
	iniciada_en TIMESTAMP WITHOUT TIME ZONE, 
	actualizada_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuario (id), 
	FOREIGN KEY(participante_id) REFERENCES participante (id), 
	FOREIGN KEY(sesion_id) REFERENCES sesion (id)
);

-- jugada: Detalle de cada jugada de una partida: quién la decidió y cómo la evaluó Stockfish.
CREATE TABLE jugada (
	id SERIAL NOT NULL, 
	partida_id VARCHAR NOT NULL, 
	numero INTEGER NOT NULL, 
	fen_antes VARCHAR NOT NULL, 
	movimiento VARCHAR NOT NULL, 
	decidido_por VARCHAR, 
	tiempo_calculo_ms INTEGER, 
	explicacion VARCHAR, 
	evaluacion_cp INTEGER, 
	mate_en INTEGER, 
	evaluacion_mejor_cp INTEGER, 
	mate_en_mejor INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(partida_id) REFERENCES partida (id)
);

-- Comentarios de tablas y columnas (visibles en pgAdmin y en el editor de Supabase)
COMMENT ON TABLE participante IS 'Estudiantes de un curso, para sesiones del facilitador.';
COMMENT ON COLUMN participante.id IS 'Identificador del participante.';
COMMENT ON COLUMN participante.nombre IS 'Nombre del participante.';
COMMENT ON TABLE sesion IS 'Sesión de clase que abre un facilitador, con su dificultad y tipo de oponente.';
COMMENT ON COLUMN sesion.id IS 'Identificador de la sesión.';
COMMENT ON COLUMN sesion.facilitador IS 'Nombre del facilitador que la abrió.';
COMMENT ON COLUMN sesion.fecha IS 'Fecha y hora de la sesión.';
COMMENT ON COLUMN sesion.dificultad IS 'Nivel de dificultad de la sesión, de 0 a 20.';
COMMENT ON COLUMN sesion.tipo_oponente IS 'motor, modelo o participante.';
COMMENT ON TABLE usuario IS 'Personas que usan el sistema, con su rol, su nivel de juego y su perfil.';
COMMENT ON COLUMN usuario.id IS 'Identificador del usuario.';
COMMENT ON COLUMN usuario.email IS 'Correo del usuario; es único y se usa para iniciar sesión.';
COMMENT ON COLUMN usuario.nombre IS 'Nombre visible.';
COMMENT ON COLUMN usuario.password_hash IS 'Hash de la contraseña (nunca se guarda en claro). Nulo si entra solo con Google.';
COMMENT ON COLUMN usuario.rol IS 'jugador o facilitador.';
COMMENT ON COLUMN usuario.creado_en IS 'Fecha y hora de registro.';
COMMENT ON COLUMN usuario.activo IS 'Indica si la cuenta está habilitada.';
COMMENT ON COLUMN usuario.google_id IS 'Identificador de Google cuando entra con su cuenta de Google.';
COMMENT ON COLUMN usuario.avatar_url IS 'Ruta o URL de la foto de perfil.';
COMMENT ON COLUMN usuario.nivel_estimado IS 'Nivel de juego vigente, de 0 a 20 (la escala del Skill Level de Stockfish). Lo recalcula el sistema al terminar cada partida, o lo fija el jugador como punto de partida desde su perfil.';
COMMENT ON COLUMN usuario.rango_estimado IS 'Principiante (niveles 0-6), Intermedio (7-13) o Avanzado (14-20).';
COMMENT ON COLUMN usuario.edad IS 'Edad, de uso libre en el perfil.';
COMMENT ON COLUMN usuario.descripcion IS 'Biografía o trayectoria breve, de uso libre en el perfil.';
COMMENT ON COLUMN usuario.preset_ensenanza IS 'Tono con el que Turing habla: infantil, estandar o adultos. Lo elige el facilitador.';
COMMENT ON TABLE calibracion IS 'Una fila por partida terminada que sirvió para medir el nivel del jugador. Con las últimas tres se calcula su nivel vigente.';
COMMENT ON COLUMN calibracion.id IS 'Identificador de la calibración.';
COMMENT ON COLUMN calibracion.usuario_id IS 'Jugador medido.';
COMMENT ON COLUMN calibracion.partida_id IS 'Partida que se usó para medir. No es clave foránea a propósito: una partida puede vivir solo en memoria y no tener fila en partida.';
COMMENT ON COLUMN calibracion.precision_global IS 'Precisión del jugador en esa partida, de 0 a 100: compara solo sus jugadas con las de Stockfish.';
COMMENT ON COLUMN calibracion.nivel_partida IS 'Nivel (0-20) que saldría mirando solamente esa partida.';
COMMENT ON COLUMN calibracion.rango_partida IS 'Rango que saldría mirando solamente esa partida.';
COMMENT ON COLUMN calibracion.total_jugadas IS 'Cantidad de jugadas del jugador que se evaluaron (mínimo 5 para registrarla).';
COMMENT ON COLUMN calibracion.creado_en IS 'Fecha y hora en que se registró.';
COMMENT ON TABLE exportacion_dataset IS 'Una fila por cada vez que un facilitador descargó el dataset de partidas para reentrenar el modelo propio (HU4, todavía pendiente de construir).';
COMMENT ON COLUMN exportacion_dataset.id IS 'Identificador de la descarga.';
COMMENT ON COLUMN exportacion_dataset.usuario_id IS 'Facilitador que descargó el dataset.';
COMMENT ON COLUMN exportacion_dataset.creado_en IS 'Fecha y hora en que se generó la descarga.';
COMMENT ON COLUMN exportacion_dataset.corte_en IS 'Instante de corte de esta descarga: la fecha más reciente entre las partidas incluidas. Sirve para saber qué partidas son "nuevas" en la próxima descarga.';
COMMENT ON COLUMN exportacion_dataset.cantidad_partidas IS 'Cuántas partidas incluyó esta descarga.';
COMMENT ON COLUMN exportacion_dataset.cantidad_jugadas IS 'Cuántas jugadas del jugador incluyó esta descarga.';
COMMENT ON COLUMN exportacion_dataset.formato IS 'Formato del archivo entregado, por ejemplo pgn+csv.';
COMMENT ON TABLE mensaje_tutor IS 'Historial de la conversación de cada jugador con el tutor Turing (memoria multi-turno).';
COMMENT ON COLUMN mensaje_tutor.id IS 'Identificador del mensaje.';
COMMENT ON COLUMN mensaje_tutor.usuario_id IS 'Jugador que conversa con el tutor.';
COMMENT ON COLUMN mensaje_tutor.rol IS 'user (lo escribió el jugador) o assistant (respondió Turing).';
COMMENT ON COLUMN mensaje_tutor.contenido IS 'Texto del mensaje.';
COMMENT ON COLUMN mensaje_tutor.creado_en IS 'Fecha y hora del mensaje.';
COMMENT ON TABLE partida IS 'Cada partida jugada: quién la jugó, contra qué oponente, a qué nivel, la posición actual y las funciones opcionales que el facilitador habilitó.';
COMMENT ON COLUMN partida.id IS 'Identificador de la partida: un UUID en hexadecimal (texto), no un número.';
COMMENT ON COLUMN partida.usuario_id IS 'Dueño de la partida. Nulo en partidas antiguas o de prueba sin dueño.';
COMMENT ON COLUMN partida.participante_id IS 'Reservado para sesiones de clase. Hoy siempre nulo.';
COMMENT ON COLUMN partida.sesion_id IS 'Reservado para sesiones de clase. Hoy siempre nulo.';
COMMENT ON COLUMN partida.fecha IS 'Fecha y hora de creación.';
COMMENT ON COLUMN partida.resultado IS '1-0, 0-1 o 1/2-1/2. Nulo mientras la partida sigue en curso o no se terminó.';
COMMENT ON COLUMN partida.tipo IS 'digital (se juega en pantalla) o fisica (con el tablero real detectado por visión).';
COMMENT ON COLUMN partida.fen IS 'Posición actual del tablero en notación FEN.';
COMMENT ON COLUMN partida.fen_inicial IS 'Posición desde la que arrancó la partida (FEN). Nulo en partidas antiguas.';
COMMENT ON COLUMN partida.nivel IS 'Nivel del oponente elegido al crear la partida, de 0 a 20. No cambia durante la partida.';
COMMENT ON COLUMN partida.tipo_oponente IS 'motor (Stockfish) o modelo (Turing, el modelo propio).';
COMMENT ON COLUMN partida.jugadas_uci IS 'Todas las jugadas en notación UCI separadas por espacio; permite reconstruir el tablero.';
COMMENT ON COLUMN partida.permite_simulacion_3d IS 'El facilitador habilitó la simulación 3D para esta partida.';
COMMENT ON COLUMN partida.permite_camara IS 'El facilitador habilitó la cámara del tablero físico para esta partida.';
COMMENT ON COLUMN partida.es_demostracion IS 'Partida que el facilitador transmite en vivo a la clase. Solo una a la vez en todo el sistema.';
COMMENT ON COLUMN partida.usa_brazo IS 'La respuesta del oponente también se ejecuta en el brazo robótico (o su simulador).';
COMMENT ON COLUMN partida.estado IS 'en_curso, terminada o abandonada. Lo administra el ciclo de vida de la partida (Sala de Control sin botón "iniciar").';
COMMENT ON COLUMN partida.iniciada_en IS 'Momento de la primera jugada del jugador humano. Nulo si todavía no jugó ninguna.';
COMMENT ON COLUMN partida.actualizada_en IS 'Momento de la última jugada aplicada (humano o estrategia). Nulo hasta la primera jugada.';
COMMENT ON TABLE jugada IS 'Detalle de cada jugada de una partida: quién la decidió y cómo la evaluó Stockfish.';
COMMENT ON COLUMN jugada.id IS 'Identificador de la jugada.';
COMMENT ON COLUMN jugada.partida_id IS 'Partida a la que pertenece.';
COMMENT ON COLUMN jugada.numero IS 'Número de la jugada dentro de la partida (1, 2, 3...). Las impares son del jugador humano.';
COMMENT ON COLUMN jugada.fen_antes IS 'Posición (FEN) justo antes de jugarla.';
COMMENT ON COLUMN jugada.movimiento IS 'Jugada en notación UCI, por ejemplo e2e4.';
COMMENT ON COLUMN jugada.decidido_por IS 'Quién la jugó: jugador, motor o modelo.';
COMMENT ON COLUMN jugada.tiempo_calculo_ms IS 'Milisegundos que tardó en calcularse. Nulo si no se midió.';
COMMENT ON COLUMN jugada.explicacion IS 'Explicación en lenguaje natural de la jugada. Nulo si no se generó.';
COMMENT ON COLUMN jugada.evaluacion_cp IS 'Evaluación de Stockfish, en centipeones, del resultado de la jugada realmente jugada.';
COMMENT ON COLUMN jugada.mate_en IS 'Si tras la jugada hay mate forzado, en cuántas jugadas. Nulo si no lo hay.';
COMMENT ON COLUMN jugada.evaluacion_mejor_cp IS 'Evaluación, en centipeones, de la mejor jugada posible en esa posición.';
COMMENT ON COLUMN jugada.mate_en_mejor IS 'Mate forzado disponible con la mejor jugada. Nulo si no lo había.';
