// Script manual, no automatizado — verifica ChessApi contra el backend real
// corriendo en localhost:8000. Se borra después de usarlo, no es parte del build.
import 'package:chessia_app/services/chess_api.dart';

Future<void> main() async {
  final api = ChessApi.instancia;

  final partida = await api.crearPartida(nivel: 3, tipoOponente: 'motor');
  final r1 = await api.mover(partida.id, 'e2e4');
  print('jugadas: ${r1.jugadas}');

  final analisis = await api.analisisCompleto(partida.id);
  for (final j in analisis) {
    print('ply=${j.numeroPly} color=${j.color} san=${j.jugadaSan} mejor=${j.mejorJugadaMotor}');
  }

  print('OK — analisis-completo parseado correctamente');
}
