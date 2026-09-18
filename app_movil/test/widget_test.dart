import 'package:flutter_test/flutter_test.dart';

import 'package:chessia_app/main.dart';
import 'package:chessia_app/services/auth_api_service.dart';
import 'package:chessia_app/services/auth_provider.dart';

/// En tests no hay plugin nativo de almacenamiento seguro: simula "sin sesión".
class _ApiSinSesion extends AuthApiService {
  @override
  Future<bool> hasStoredToken() async => false;
}

Future<void> _arrancarApp(WidgetTester tester) async {
  await tester.pumpWidget(ChessIAApp(auth: AuthProvider(api: _ApiSinSesion())));
  await tester.pump(); // splash
  await tester.pump(); // redirect a /login una vez resuelta la sesión
}

void main() {
  testWidgets('Sin sesión guardada, la app arranca en la pantalla de login', (WidgetTester tester) async {
    await _arrancarApp(tester);

    expect(find.text('Iniciar sesión'), findsOneWidget);
    expect(find.text('Entrar'), findsOneWidget);
  });

  testWidgets('Desde login se puede pasar al formulario de registro', (WidgetTester tester) async {
    await _arrancarApp(tester);

    await tester.tap(find.text('Regístrate'));
    await tester.pump();

    expect(find.text('Crear cuenta'), findsOneWidget);
    expect(find.text('Registrarse'), findsOneWidget);
    expect(find.text('Confirmar contraseña'), findsOneWidget);
  });

  testWidgets('El formulario valida email y contraseña antes de llamar al backend', (WidgetTester tester) async {
    await _arrancarApp(tester);

    await tester.tap(find.text('Entrar'));
    await tester.pump();

    expect(find.text('Ingresa tu email'), findsOneWidget);
    expect(find.text('Ingresa tu contraseña'), findsOneWidget);
  });
}
