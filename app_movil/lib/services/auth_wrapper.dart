import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';

class AuthWrapper extends StatelessWidget {
  final Widget child;
  final Widget Function(BuildContext, AuthProvider)? loadingBuilder;

  const AuthWrapper({
    super.key,
    required this.child,
    this.loadingBuilder,
  });

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: Consumer<AuthProvider>(
        builder: (context, auth, _) {
          if (auth.isLoading) {
            return loadingBuilder?.call(context, auth) ??
                const Center(child: CircularProgressIndicator());
          }
          return child;
        },
      ),
    );
  }
}