import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../widgets.dart';
import '../services.dart';

/// Pantalla de acceso de la app móvil: registro e inicio de sesión contra
/// `/auth/*` del backend. Solo entran cuentas con rol `jugador`; al entrar,
/// el router (`main.dart`) redirige solo a `/onboarding`.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _isLogin = true; // true = login, false = registro

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return _LoginView(
      auth: auth,
      isLogin: _isLogin,
      onToggle: () {
        auth.clearError();
        setState(() => _isLogin = !_isLogin);
      },
    );
  }
}

class _LoginView extends StatefulWidget {
  final AuthProvider auth;
  final bool isLogin;
  final VoidCallback onToggle;

  const _LoginView({
    required this.auth,
    required this.isLogin,
    required this.onToggle,
  });

  @override
  State<_LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<_LoginView> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            _BackgroundIllustration(),
            Positioned(
              top: AppSpacing.spaceSm,
              right: AppSpacing.spaceSm,
              child: IconButton(
                tooltip: 'Servidor',
                icon: const Icon(Icons.dns_outlined, color: AppColors.onSurfaceVariant),
                onPressed: () => _configurarServidor(context),
              ),
            ),
            SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.margin),
              child: Column(
                children: [
                  const SizedBox(height: AppSpacing.spaceXl),
                  _BrandLogo(),
                  const SizedBox(height: AppSpacing.spaceXl),
                  GlassCard(
                    padding: const EdgeInsets.all(AppSpacing.spaceXl),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            widget.isLogin ? 'Iniciar sesión' : 'Crear cuenta',
                            style: AppTextStyles.headlineLg.copyWith(
                              color: AppColors.onSurface,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: AppSpacing.spaceXl),
                          if (!widget.isLogin) ...[
                            _NameField(controller: _nameController),
                            const SizedBox(height: AppSpacing.spaceMd),
                          ],
                          _EmailField(controller: _emailController),
                          const SizedBox(height: AppSpacing.spaceMd),
                          _PasswordField(
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            onToggleVisibility: () => setState(() => _obscurePassword = !_obscurePassword),
                            label: 'Contraseña',
                          ),
                          if (!widget.isLogin) ...[
                            const SizedBox(height: AppSpacing.spaceMd),
                            _PasswordField(
                              controller: _confirmPasswordController,
                              obscureText: _obscureConfirmPassword,
                              onToggleVisibility: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
                              label: 'Confirmar contraseña',
                              validator: (value) {
                                if (value != _passwordController.text) {
                                  return 'Las contraseñas no coinciden';
                                }
                                return null;
                              },
                            ),
                          ],
                          if (widget.auth.error != null) ...[
                            const SizedBox(height: AppSpacing.spaceMd),
                            _ErrorMessage(error: widget.auth.error!),
                          ],
                          const SizedBox(height: AppSpacing.spaceXl),
                          FilledButton(
                            onPressed: widget.auth.isLoading ? null : _submit,
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceMd),
                              backgroundColor: AppColors.primary,
                            ),
                            child: widget.auth.isLoading
                                ? const SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(AppColors.onPrimary),
                                    ),
                                  )
                                : Text(
                                    widget.isLogin ? 'Entrar' : 'Registrarse',
                                    style: AppTextStyles.labelMd.copyWith(fontSize: 16),
                                  ),
                          ),
                          const SizedBox(height: AppSpacing.spaceLg),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                widget.isLogin
                                    ? '¿No tienes cuenta? '
                                    : '¿Ya tienes cuenta? ',
                                style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
                              ),
                              TextButton(
                                onPressed: widget.onToggle,
                                child: Text(
                                  widget.isLogin ? 'Regístrate' : 'Inicia sesión',
                                  style: AppTextStyles.labelMd.copyWith(
                                    color: AppColors.primary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.spaceMd),
                  Text(
                    'Servidor: ${ApiConfig.baseUrl}',
                    style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.spaceXl),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Diálogo para apuntar la app a otra IP del backend (p. ej. la Mac en la
  /// red de la U) sin recompilar. Se guarda en el dispositivo.
  Future<void> _configurarServidor(BuildContext context) async {
    final controller = TextEditingController(text: ApiConfig.baseUrl);
    String? estado;
    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Servidor del backend'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: controller,
                keyboardType: TextInputType.url,
                autocorrect: false,
                decoration: const InputDecoration(
                  labelText: 'URL',
                  hintText: 'http://192.168.1.50:8000',
                ),
              ),
              const SizedBox(height: AppSpacing.spaceSm),
              Text(
                'Por defecto: ${ApiConfig.porDefecto}',
                style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
              ),
              if (estado != null) ...[
                const SizedBox(height: AppSpacing.spaceSm),
                Text(estado!, style: AppTextStyles.bodySm.copyWith(color: AppColors.primary)),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () async {
                await ApiConfig.guardar(controller.text);
                final ok = await ChessApi.instancia.backendEnLinea();
                setDialogState(() => estado = ok ? 'Conectado ✓' : 'Sin respuesta del backend');
              },
              child: const Text('Probar'),
            ),
            TextButton(
              onPressed: () async {
                await ApiConfig.guardar(null);
                if (context.mounted) Navigator.of(context).pop();
              },
              child: const Text('Por defecto'),
            ),
            FilledButton(
              onPressed: () async {
                await ApiConfig.guardar(controller.text);
                if (context.mounted) Navigator.of(context).pop();
              },
              child: const Text('Guardar'),
            ),
          ],
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final email = _emailController.text.trim();
    final password = _passwordController.text;

    bool success;
    if (widget.isLogin) {
      success = await widget.auth.login(email: email, password: password);
    } else {
      success = await widget.auth.register(
        email: email,
        password: password,
        nombre: _nameController.text.trim(),
      );
    }

    // El redirect del router ya lleva a /onboarding cuando cambia la sesión;
    // este go() solo cubre el caso en que la ruta no se haya refrescado aún.
    if (success && mounted) {
      context.go('/onboarding');
    }
  }
}

class _BackgroundIllustration extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: Column(
        children: [
          Expanded(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    AppColors.surfaceContainerLowest,
                    AppColors.surfaceContainerLowest,
                    AppColors.surfaceContainerLow,
                  ],
                  stops: [0.0, 0.65, 1.0],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BrandLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Image.asset(
          'assets/images/logo.png',
          width: 150,
          height: 150,
          fit: BoxFit.contain,
          semanticLabel: 'Logo ChessIA',
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Text.rich(
          TextSpan(
            style: const TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 43,
              fontWeight: FontWeight.w800,
              height: 1.0,
            ),
            children: const [
              TextSpan(text: 'Chess', style: TextStyle(color: AppColors.onSurface)),
              TextSpan(text: 'I', style: TextStyle(color: Color(0xFF15B271), fontWeight: FontWeight.w900)),
              TextSpan(text: 'A', style: TextStyle(fontWeight: FontWeight.w900)),
            ],
          ),
        ),
      ],
    );
  }
}

class _EmailField extends StatelessWidget {
  final TextEditingController controller;

  const _EmailField({required this.controller});

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: 'Email',
        hintText: 'tu@email.com',
        prefixIcon: const Icon(Icons.email_outlined),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) return 'Ingresa tu email';
        if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
          return 'Email inválido';
        }
        return null;
      },
    );
  }
}

class _NameField extends StatelessWidget {
  final TextEditingController controller;

  const _NameField({required this.controller});

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      textInputAction: TextInputAction.next,
      textCapitalization: TextCapitalization.words,
      decoration: InputDecoration(
        labelText: 'Nombre',
        hintText: 'Tu nombre',
        prefixIcon: const Icon(Icons.person_outline),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) return 'Ingresa tu nombre';
        if (value.trim().length < 2) return 'Nombre muy corto';
        return null;
      },
    );
  }
}

class _PasswordField extends StatelessWidget {
  final TextEditingController controller;
  final bool obscureText;
  final VoidCallback onToggleVisibility;
  final String label;
  final String? Function(String?)? validator;

  const _PasswordField({
    required this.controller,
    required this.obscureText,
    required this.onToggleVisibility,
    required this.label,
    this.validator,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: label,
        hintText: '••••••••',
        prefixIcon: const Icon(Icons.lock_outline),
        suffixIcon: IconButton(
          icon: Icon(obscureText ? Icons.visibility_outlined : Icons.visibility_off_outlined),
          onPressed: onToggleVisibility,
        ),
      ),
      validator: validator ??
          (value) {
            if (value == null || value.isEmpty) return 'Ingresa tu contraseña';
            if (value.length < 6) return 'Mínimo 6 caracteres';
            return null;
          },
    );
  }
}

class _ErrorMessage extends StatelessWidget {
  final String error;

  const _ErrorMessage({required this.error});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceMd),
      surfaceColor: AppColors.errorContainer,
      borderColor: AppColors.error.withOpacity(0.3),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: AppColors.error, size: 20),
          const SizedBox(width: AppSpacing.spaceSm),
          Expanded(
            child: Text(
              error,
              style: AppTextStyles.bodySm.copyWith(color: AppColors.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}