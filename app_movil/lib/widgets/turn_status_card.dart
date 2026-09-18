import 'package:flutter/material.dart';
import '../theme.dart';
import 'glass_card.dart';

/// Fila "de quién es el turno" + reloj — usada tanto en la partida normal
/// como en el diagnóstico. El reloj es un cronómetro real (cuenta segundos
/// de verdad) pero decorativo: el backend no tiene control de tiempo, así
/// que nunca fuerza fin de partida por reloj.
class TurnStatusCard extends StatelessWidget {
  final bool esTurnoBlancas;
  final Duration tiempoRestante;

  const TurnStatusCard({
    super.key,
    required this.esTurnoBlancas,
    required this.tiempoRestante,
  });

  String _formatearTiempo(Duration d) {
    final minutos = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final segundos = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutos:$segundos';
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.spaceLg, vertical: AppSpacing.spaceMd),
      child: Row(
        children: [
          Container(
            width: 22,
            height: 22,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: esTurnoBlancas ? Colors.white : Colors.black,
              border: Border.all(color: AppColors.outlineVariant, width: 1.5),
            ),
          ),
          const SizedBox(width: AppSpacing.spaceMd),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Tu turno', style: AppTextStyles.bodyLg.copyWith(color: AppColors.onSurface, fontWeight: FontWeight.w700)),
              Text(
                esTurnoBlancas ? 'Blancas' : 'Negras',
                style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
              ),
            ],
          ),
          const Spacer(),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.access_time, size: 15, color: AppColors.onSurfaceVariant),
                  const SizedBox(width: 4),
                  Text(
                    _formatearTiempo(tiempoRestante),
                    style: AppTextStyles.telemetryMd.copyWith(color: AppColors.onSurface, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
              Text('Tiempo restante', style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant)),
            ],
          ),
        ],
      ),
    );
  }
}
