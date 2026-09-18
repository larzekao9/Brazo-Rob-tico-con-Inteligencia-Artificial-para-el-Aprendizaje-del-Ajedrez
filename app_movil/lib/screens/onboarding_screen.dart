import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../widgets.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<OnboardingCard> _cards = [
    OnboardingCard(
      piece: '♔',
      name: 'El Rey',
      description: 'La pieza más importante. Si cae, pierdes la partida. Se mueve una casilla en cualquier dirección.',
      movePattern: 'Una casilla en cualquier dirección',
      exampleFen: '8/8/8/8/8/8/8/4K3 w - - 0 1',
    ),
    OnboardingCard(
      piece: '♕',
      name: 'La Dama',
      description: 'La pieza más poderosa. Combina el movimiento de torre y alfil: líneas rectas y diagonales.',
      movePattern: 'Cualquier número de casillas en línea recta o diagonal',
      exampleFen: '8/8/8/8/8/8/8/3Q4 w - - 0 1',
    ),
    OnboardingCard(
      piece: '♖',
      name: 'La Torre',
      description: 'Se mueve en líneas rectas (horizontal y vertical). Participa en el enroque con el rey.',
      movePattern: 'Cualquier número de casillas en horizontal o vertical',
      exampleFen: '8/8/8/8/8/8/8/R7 w - - 0 1',
    ),
    OnboardingCard(
      piece: '♗',
      name: 'El Alfil',
      description: 'Se mueve solo en diagonales. Cada alfil siempre permanece en casillas del mismo color.',
      movePattern: 'Cualquier número de casillas en diagonal',
      exampleFen: '8/8/8/8/8/8/8/2B5 w - - 0 1',
    ),
    OnboardingCard(
      piece: '♘',
      name: 'El Caballo',
      description: 'La única pieza que salta otras. Se mueve en "L": dos casillas en una dirección y una perpendicular.',
      movePattern: 'En forma de L (2+1 casillas)',
      exampleFen: '8/8/8/8/8/8/8/1N6 w - - 0 1',
    ),
    OnboardingCard(
      piece: '♙',
      name: 'El Peón',
      description: 'Avanza una casilla (dos en su primer movimiento), captura en diagonal. Promociona al llegar al final.',
      movePattern: 'Una casilla adelante, captura en diagonal',
      exampleFen: '8/8/8/8/8/8/8/P7 w - - 0 1',
    ),
    OnboardingCard(
      piece: '♚♛',
      name: 'Jaque y Jaque Mate',
      description: 'Jaque: el rey está bajo ataque. Jaque mate: el rey no puede escapar → fin de la partida.',
      movePattern: 'El rey no tiene movimientos legales para escapar',
      exampleFen: '4k3/8/8/8/8/8/8/4K2R w K - 0 1',
    ),
    OnboardingCard(
      piece: '🏰',
      name: 'Enroque',
      description: 'Movimiento especial del rey y torre. Rey mueve 2 casillas hacia la torre, torre salta al lado del rey.',
      movePattern: 'Rey 2 casillas + torre al lado',
      exampleFen: 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
    ),
    OnboardingCard(
      piece: '⚡',
      name: 'Tablas',
      description: 'Empate por: ahogado (rey sin movimientos legales y no en jaque), repetición, 50 movimientos sin captura/peón, material insuficiente.',
      movePattern: 'El rey no está en jaque pero no tiene movimientos legales',
      exampleFen: '7k/5Q2/5K2/8/8/8/8/8 b - - 0 1',
    ),
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(
              currentPage: _currentPage,
              totalPages: _cards.length,
              onBack: () => _pageController.previousPage(
                duration: const Duration(milliseconds: 250),
                curve: Curves.easeOut,
              ),
              onSkip: _completeOnboarding,
            ),
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                itemCount: _cards.length,
                onPageChanged: (index) => setState(() => _currentPage = index),
                itemBuilder: (context, index) => _OnboardingCardView(
                  card: _cards[index],
                  isLast: index == _cards.length - 1,
                  onComplete: () => _completeOnboarding(),
                ),
              ),
            ),
            _BottomIndicator(
              currentPage: _currentPage,
              totalPages: _cards.length,
            ),
          ],
        ),
      ),
    );
  }

  void _completeOnboarding() {
    // TODO: Guardar onboarding_completado = true en shared_preferences
    context.go('/mode-selection');
  }
}

class _TopBar extends StatelessWidget {
  final int currentPage;
  final int totalPages;
  final VoidCallback onBack;
  final VoidCallback onSkip;

  const _TopBar({
    required this.currentPage,
    required this.totalPages,
    required this.onBack,
    required this.onSkip,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          if (currentPage > 0)
            IconButton(
              onPressed: onBack,
              icon: const Icon(Icons.chevron_left, color: AppColors.onSurface),
            )
          else
            const SizedBox(width: 48),
          Text(
            '${currentPage + 1} / $totalPages',
            style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
          ),
          TextButton(
            onPressed: onSkip,
            child: Text(
              'Saltar',
              style: AppTextStyles.labelMd.copyWith(color: AppColors.secondary),
            ),
          ),
        ],
      ),
    );
  }
}

class _OnboardingCardView extends StatelessWidget {
  final OnboardingCard card;
  final bool isLast;
  final VoidCallback onComplete;

  const _OnboardingCardView({
    required this.card,
    required this.isLast,
    required this.onComplete,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          GlassCard(
            padding: const EdgeInsets.all(AppSpacing.spaceXl),
            child: Column(
              children: [
                Text(
                  card.piece,
                  style: const TextStyle(fontSize: 80, fontFamily: 'PlusJakartaSans'),
                ),
                const SizedBox(height: AppSpacing.spaceLg),
                Text(
                  card.name,
                  style: AppTextStyles.headlineLg.copyWith(color: AppColors.onSurface),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.spaceMd),
                Text(
                  card.description,
                  style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.spaceLg),
                Container(
                  padding: const EdgeInsets.all(AppSpacing.spaceMd),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: AppRadius.radiusLg,
                  ),
                  child: Column(
                    children: [
                      Text(
                        'Movimiento:',
                        style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant),
                      ),
                      const SizedBox(height: AppSpacing.spaceXs),
                      Text(
                        card.movePattern,
                        style: AppTextStyles.bodyMd.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          if (isLast)
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: onComplete,
                child: const Text('Comenzar'),
              ),
            ),
        ],
      ),
    );
  }
}

class _BottomIndicator extends StatelessWidget {
  final int currentPage;
  final int totalPages;

  const _BottomIndicator({
    required this.currentPage,
    required this.totalPages,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(totalPages, (index) {
          return AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            margin: const EdgeInsets.symmetric(horizontal: 4),
            width: currentPage == index ? 24 : 8,
            height: 8,
            decoration: BoxDecoration(
              color: currentPage == index ? AppColors.primary : AppColors.outlineVariant,
              borderRadius: AppRadius.radiusFull,
            ),
          );
        }),
      ),
    );
  }
}

class OnboardingCard {
  final String piece;
  final String name;
  final String description;
  final String movePattern;
  final String exampleFen;

  const OnboardingCard({
    required this.piece,
    required this.name,
    required this.description,
    required this.movePattern,
    required this.exampleFen,
  });
}