import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
// Se eliminó flutter_bloc porque no se usa aquí

import '../../logic/auth_cubit/auth_cubit.dart';
import '../../logic/auth_cubit/auth_state.dart';
import '../../presentation/features/login/screens/login_screen.dart';
import '../../presentation/features/home/screens/home_screen.dart';
import '../../presentation/shared/layouts/responsive_layout.dart';
import '../../presentation/shared/layouts/mobile_layout.dart';
import '../../presentation/shared/layouts/desktop_layout.dart';

class AppRouter {
  static GoRouter router(AuthCubit authCubit) {
    return GoRouter(
      initialLocation: '/home',
      refreshListenable: GoRouterRefreshStream(authCubit.stream),
      redirect: (context, state) {
        final authState = authCubit.state;
        
        // CORRECCIÓN: state.location ya no existe, usamos state.uri.toString()
        final String currentLocation = state.uri.toString();
        
        final bool isLoggingIn = currentLocation == '/login';
        final bool isLoggedIn = authState.status == AuthStatus.authenticated;

        // Si no está logueado y no está en login -> ir a login
        if (!isLoggedIn && !isLoggingIn) {
          return '/login';
        }

        // Si está logueado y trata de ir a login -> ir a home
        if (isLoggedIn && isLoggingIn) {
          return '/home';
        }

        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        ShellRoute(
          builder: (context, state, child) {
            // CORRECCIÓN: Usamos state.uri.toString() para pasar la ubicación actual
            final String currentLocation = state.uri.toString();
            
            return ResponsiveLayout(
              mobileLayout: MobileLayout(location: currentLocation, child: child),
              desktopLayout: DesktopLayout(location: currentLocation, child: child),
            );
          },
          routes: [
            GoRoute(
              path: '/home',
              builder: (context, state) => const HomeScreen(),
            ),
            GoRoute(
              path: '/movement',
              builder: (context, state) => const Scaffold(
                body: Center(child: Text("Pantalla Movimientos (Scanner)")),
              ),
            ),
            GoRoute(
              path: '/inventory',
              builder: (context, state) => const Scaffold(
                body: Center(child: Text("Pantalla Inventario")),
              ),
            ),
            GoRoute(
              path: '/maintenance',
              builder: (context, state) => const Scaffold(
                body: Center(child: Text("Pantalla Mantenimiento")),
              ),
            ),
            GoRoute(
              path: '/users',
              builder: (context, state) => const Scaffold(
                body: Center(child: Text("Pantalla Usuarios")),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class GoRouterRefreshStream extends ChangeNotifier {
  late final StreamSubscription<dynamic> _subscription;

  GoRouterRefreshStream(Stream<dynamic> stream) {
    notifyListeners();
    _subscription = stream.asBroadcastStream().listen(
      (_) => notifyListeners(),
    );
  }

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}