# chessia_app — app móvil (Flutter)

App móvil del jugador. Consume el mismo backend FastAPI que la Sala de Control
web (`backend/`): no tiene datos simulados propios.

## Acceso (registro / inicio de sesión)

- La app es **solo para cuentas con rol `jugador`**. "Registrarse" crea siempre
  un jugador, y "Entrar" manda `rol_esperado: "jugador"` al backend: una cuenta
  con otro rol (por ejemplo `facilitador`) recibe 403 y no entra.
- Los tokens JWT quedan en almacenamiento seguro del dispositivo; al reabrir la
  app se valida la sesión contra `/auth/me` y, si sigue viva, se salta el login.
- Sin sesión, cualquier ruta redirige a `/login`. Con sesión, se puede navegar a
  todas las demás pantallas. "Cerrar sesión" está en la pestaña Perfil de Home.

## Levantar todo en local

1. Backend con base de datos (auth necesita `DATABASE_URL`; SQLite sirve para
   desarrollo, Postgres para lo definitivo):

   ```bash
   cd Ajedrez
   DATABASE_URL=sqlite:///./test.db uvicorn backend.main:app --reload
   ```

   Si la base ya existía sin la columna `usuario.rol`, el backend la agrega
   solo al arrancar.

   Para que un celular físico llegue al backend hay que escuchar en todas las
   interfaces, no solo en localhost:

   ```bash
   DATABASE_URL=sqlite:///./test.db uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

2. App móvil:

   ```bash
   cd app_movil
   flutter run                       # emulador Android -> 10.0.2.2:8000, simulador iOS -> 127.0.0.1:8000
   flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000   # celular físico en la misma red
   ```

### iPhone físico

- Requisitos: Xcode con una cuenta de desarrollador configurada (el proyecto ya
  tiene `DEVELOPMENT_TEAM` y firma automática), CocoaPods, y el iPhone con
  Modo Desarrollador activado y conectado por USB. `flutter devices` tiene que
  listarlo.
- La Mac y el iPhone deben estar en la **misma red Wi-Fi**. La IP de la Mac se
  obtiene con `ipconfig getifaddr en0`.
- `ios/Runner/Info.plist` ya permite HTTP en claro hacia la red local
  (`NSAppTransportSecurity`) y declara el uso de red local que iOS pide.
- **Si el repo está en una carpeta sincronizada con iCloud** (Escritorio o
  Documentos), `flutter build ios` falla con `Exited with status code 255`:
  iCloud agrega metadatos de Finder al framework de Flutter y `codesign` los
  rechaza ("detritus not allowed"). Solución: que `app_movil/build` sea un
  enlace simbólico a una carpeta fuera de iCloud.

  ```bash
  cd app_movil
  flutter clean                      # borra build/ si existía
  mkdir -p ~/develop/flutter_build/chessia_app
  ln -s ~/develop/flutter_build/chessia_app build
  ```

  `flutter clean` borra el enlace; si después de un clean vuelve el error 255,
  repetí el `ln -s`. No usar `flutter config --build-dir` con rutas `..`:
  rompe `flutter test`.
- Compilar e instalar (reemplazar la IP por la de tu Mac):

  ```bash
  flutter build ios --release --dart-define=API_BASE_URL=http://192.168.101.10:8000
  flutter install --release -d <udid del iPhone>
  ```

  o directamente `flutter run --release -d <udid> --dart-define=...`.
- Si la IP de la Mac cambia (otra red), no hace falta recompilar: en la
  pantalla de login, el ícono de servidor (arriba a la derecha) permite
  escribir la URL nueva, probarla y guardarla en el teléfono.
- La primera vez que se instala con una cuenta gratuita de Apple, el iPhone
  pide confiar en el desarrollador en Ajustes > General > VPN y gestión de
  dispositivos.

## Tests

```bash
flutter analyze
flutter test
```

Los tests de widgets no tocan red ni almacenamiento nativo: inyectan un
`AuthProvider` con un servicio falso (ver `test/widget_test.dart`).
