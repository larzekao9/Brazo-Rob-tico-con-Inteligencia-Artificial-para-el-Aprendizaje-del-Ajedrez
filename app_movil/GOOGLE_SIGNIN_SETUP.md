# Configuración de Google Sign-In — ChessIA

## Resumen de credenciales

| Plataforma | Client ID | Estado |
|------------|-----------|--------|
| **Android** | `840567566478-qopmqu3qk27hcp0d60vkil2urcsb0l3i.apps.googleusercontent.com` | ✅ Configurado (package + SHA-1) |
| **iOS** | `840567566478-1a8nnn7659lsfvt7pf8q9p2k2bb5op78.apps.googleusercontent.com` | ✅ `GoogleService-Info.plist` copiado |
| **Web (serverClientId)** | `840567566478-qopmqu3qk27hcp0d60vkil2urcsb0l3i.apps.googleusercontent.com` | ⚠️ Usa el mismo que Android (installed type) |

> **Nota**: El `serverClientId` en `auth_service.dart` usa el Android client ID. Para producción, crea un **Web Application** OAuth client separado en Google Cloud Console y úsalo como `serverClientId`.

---

## Android — Configuración completada

### Package name / Application ID
```
com.ajedrez.chessia.chessiaApp
```

### SHA-1 (debug keystore)
```
02:9F:89:2D:0A:5F:E3:97:CA:18:A8:60:AB:11:5C:58:12:87:AC:5B
```

### Archivos creados
- `android/app/google-services.json` — Template con project_id y client_id
- `android/build.gradle.kts` — Agregado `classpath("com.google.gms:google-services:4.4.1")`
- `android/app/build.gradle.kts` — Agregado plugin `com.google.gms.google-services` + package name actualizado

### Qué falta en Google Cloud Console
1. Ve a **APIs & Services → Credentials**
2. Crea/edita OAuth 2.0 Client ID → **Android**
   - Package name: `com.ajedrez.chessia.chessiaApp`
   - SHA-1: `02:9F:89:2D:0A:5F:E3:97:CA:18:A8:60:AB:11:5C:58:12:87:AC:5B`
3. (Opcional) Crea un **Web Application** client para `serverClientId` separado

---

## iOS — Configuración completada

### Bundle ID
```
com.ajedrez.chessia.chessiaApp
```

### Archivos creados
- `ios/Runner/GoogleService-Info.plist` — Copiado del archivo proporcionado
- `ios/Runner/Info.plist` — `CFBundleURLScheme` actualizado a `com.googleusercontent.apps.840567566478-1a8nnn7659lsfvt7pf8q9p2k2bb5op78`

### Qué falta en Google Cloud Console
1. OAuth 2.0 Client ID → **iOS**
   - Bundle ID: `com.ajedrez.chessia.chessiaApp`

---

## serverClientId (para verificación de ID tokens en backend)

Actualmente en `lib/services/auth_service.dart:13`:
```dart
serverClientId: '840567566478-qopmqu3qk27hcp0d60vkil2urcsb0l3i.apps.googleusercontent.com',
```

**Recomendación**: Crea un **Web Application** OAuth client separado en Google Cloud Console:
1. Credentials → Create Credentials → OAuth client ID → **Web application**
2. Authorized redirect URIs: `https://tu-backend.com/auth/google/callback` (o `http://localhost:8000/auth/google/callback` para dev)
3. Copia el Client ID resultante → actualízalo en `auth_service.dart`

---

## Probar

```bash
cd /Users/larzekao/Desktop/Universidad/9\ no\ Semestre/taller\ de\ gardo\ /Ajedrez/app_movil
flutter pub get
flutter run
```

### Verificar configuración Android
```bash
cd android && ./gradlew signingReport | grep SHA1
```

### Verificar bundle ID iOS
```bash
grep PRODUCT_BUNDLE_IDENTIFIER ios/Runner.xcodeproj/project.pbxproj | head -1
```

---

## Troubleshooting

| Error | Causa | Solución |
|-------|-------|----------|
| `DEVELOPER_ERROR` (Android) | Package name o SHA-1 no coinciden | Verifica en Google Cloud Console |
| `invalid_client` (iOS) | Bundle ID no coincide | Verifica `PRODUCT_BUNDLE_IDENTIFIER` |
| `sign_in_failed` (ambos) | OAuth consent screen no publicado | Publica la app en OAuth consent screen |
| `missing google-services.json` | No se generó el archivo | Ejecuta `flutter pub get` y `flutter run` |

---

## Archivos modificados en esta sesión

```
android/
├── build.gradle.kts                    # + google-services classpath
├── app/
│   ├── build.gradle.kts                # + plugin + package name
│   └── google-services.json            # Template (completar API key)

ios/
├── Runner/
│   ├── GoogleService-Info.plist        # Copiado
│   └── Info.plist                      # + CFBundleURLScheme

lib/
└── services/
    └── auth_service.dart               # serverClientId actualizado
```