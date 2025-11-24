import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../logic/auth_cubit/auth_cubit.dart';
import '../../logic/auth_cubit/auth_state.dart';
import '../../presentation/features/login/screens/login_screen.dart';
import '../../presentation/features/home/screens/home_screen.dart';
import '../../presentation/shared/layouts/responsive_layout.dart';
import '../../presentation/shared/layouts/mobile_layout.dart';
import '../../presentation/shared/layouts/desktop_layout.dart';
import '../../presentation/features/movement/screens/scanner_screen.dart'; 
import '../../presentation/features/inventory/screens/inventory_grid_screen.dart';
import '../../presentation/features/maintenance/screens/maintenance_screen.dart'; 
import '../../presentation/features/maintenance/screens/incident_form_screen.dart'; 


class AppRouter {
  static GoRouter router(AuthCubit authCubit) {
    return GoRouter(
      initialLocation: '/home',
      refreshListenable: GoRouterRefreshStream(authCubit.stream),
      redirect: (context, state) {
        final authState = authCubit.state;
        final String currentLocation = state.uri.toString();
        final bool isLoggingIn = currentLocation == '/login';
        final bool isLoggedIn = authState.status == AuthStatus.authenticated;

        if (!isLoggedIn && !isLoggingIn) {
          return '/login';
        }

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
            
            // 2. 
            GoRoute(
              path: '/movement',
              builder: (context, state) => const ScannerScreen(),
            ),
            
            GoRoute(
              path: '/inventory',
              builder: (context, state) => const InventoryGridScreen(),  
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
            GoRoute(
              path: '/maintenance',
              builder: (context, state) => const MaintenanceScreen(),
            ),
            // Nueva ruta fuera del menú principal (pantalla completa)
            GoRoute(
              path: '/incidencia/new',
              builder: (context, state) {
                // Extraemos el parámetro opcional ?equipoId=123
                final eqParam = state.uri.queryParameters['equipoId'];
                final eqId = eqParam != null ? int.tryParse(eqParam) : null;
                return IncidentFormScreen(equipoId: eqId);
              },
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