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
| `CLAVE_REGISTRO_FACILITADOR` | Clave fuerte. **Si no se define vale `admin123`** y cualquiera podría registrarse como facilitador |
| `CORREOS_FACILITADORES` | Solo correos reales. Quitar `facilitador@test.com` y `admin@kairos-chess.ai` |
| `SEMBRAR_USUARIOS_PRUEBA` | `false` (en Supabase ya se desactiva solo, pero conviene dejarlo explícito) |
| `GOOGLE_CLIENT_ID`, `GROQ_API_KEY`, `GROQ_MODEL` | Los reales |

## 4. Primer facilitador
La base queda sin usuarios. Crear el primero registrándose en la aplicación con rol Facilitador y la
`CLAVE_REGISTRO_FACILITADOR`, o entrando con Google con un correo de `CORREOS_FACILITADORES`.

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
