import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'local_auth_provider.dart';

class LocalAuthWrapper extends StatelessWidget {
  final Widget child;
  final Widget Function(BuildContext, LocalAuthProvider)? loadingBuilder;

  const LocalAuthWrapper({
    super.key,
    required this.child,
    this.loadingBuilder,
  });

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => LocalAuthProvider(),
      child: Consumer<LocalAuthProvider>(
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