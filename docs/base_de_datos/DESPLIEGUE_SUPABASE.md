# Desplegar la base de datos en Supabase

Supabase aloja solo la base (PostgreSQL). El backend FastAPI, Stockfish y el checkpoint del modelo
siguen necesitando su propio servidor (ver [despliegue_nube.md](../despliegue_nube.md)).

## 1. Crear las tablas
1. Supabase > proyecto nuevo (guardar la contraseña de la base).
2. **SQL Editor > New query**, pegar todo [base_supabase_produccion.sql](base_supabase_produccion.sql) y **Run**.
3. Al final debe listar las 7 tablas con `rowsecurity = true`. Se puede ejecutar más de una vez sin problema.

## 2. Conectar el backend
En **Project Settings > Database > Connection string** usar el **Session pooler** (funciona con IPv4;
la conexión directa `db.<ref>.supabase.co` suele ser solo IPv6 y falla en muchos hostings):

```
DATABASE_URL=postgresql+psycopg2://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

Si la contraseña tiene caracteres especiales hay que codificarlos (`@` = `%40`, `#` = `%23`, `/` = `%2F`).

## 3. Variables del backend en el hosting (antes del primer arranque)
| Variable | Valor en producción |
| :-- | :-- |
| `DATABASE_URL` | La de arriba |
| `JWT_SECRET_KEY` | Cadena aleatoria larga (no la del ejemplo) |
| `CORREOS_FACILITADORES` | Solo el correo del primer administrador (sin patrones como `*@test.com`). Ya no hay ningún correo autorizado de fábrica ni PIN fijo: los demás facilitadores se crean con códigos de invitación |
| `SEMBRAR_USUARIOS_PRUEBA` | `false` (en Supabase ya se desactiva solo, pero conviene dejarlo explícito) |
| `GOOGLE_CLIENT_ID`, `GROQ_API_KEY`, `GROQ_MODEL` | Los reales |

## 4. Primer facilitador
La base queda sin usuarios. Crear el primero registrándose en la aplicación con rol Facilitador y un
correo de `CORREOS_FACILITADORES` (con correo y contraseña, o entrando con Google). Después, ese
facilitador invita a los demás desde **Gestión de Usuarios → Invitar a un nuevo facilitador**: genera un
código de un solo uso que vence a los pocos minutos y se lo da a la persona nueva. Cuando ya hay
facilitadores, se puede vaciar `CORREOS_FACILITADORES`.

## 5. Comprobar
```sql
SELECT count(*) FROM usuario;   -- 0 al desplegar, 1 tras crear el facilitador
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
```

## Por qué RLS
Supabase publica una API REST sobre el esquema `public`. Sin Row Level Security, quien tenga la clave pública
del proyecto podría leer `usuario` (con los hashes de contraseña). El script lo activa y quita el acceso a
`anon` y `authenticated`. El backend no usa esa API: entra como `postgres`, que no se ve afectado.

## Regenerar los scripts
Si cambia el modelo (`backend/modelos/tablas_orm.py`): `python docs/base_de_datos/generar_esquema.py`.
