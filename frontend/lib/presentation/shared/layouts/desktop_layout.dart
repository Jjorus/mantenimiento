import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../logic/auth_cubit/auth_cubit.dart'; // Import Correcto
import 'menu_config.dart';

class DesktopLayout extends StatelessWidget {
  final Widget child;
  final String location;

  const DesktopLayout({super.key, required this.child, required this.location});

  @override
  Widget build(BuildContext context) {
    final user = context.select((AuthCubit c) => c.state.user);
    final userRole = user?.role ?? 'OPERARIO';

    final visibleItems = appMenuItems.where((item) {
      return item.allowedRoles.isEmpty || item.allowedRoles.contains(userRole);
    }).toList();

    int currentIndex = visibleItems.indexWhere((item) => item.route == location);
    if (currentIndex < 0) currentIndex = 0;

    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: currentIndex,
            onDestinationSelected: (index) {
              context.go(visibleItems[index].route);
            },
            labelType: NavigationRailLabelType.all,
            leading: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Icon(
                Icons.engineering,
                size: 40,
                color: Theme.of(context).primaryColor,
              ),
            ),
            // CORRECCIÓN: Padding en lugar de Expanded
            trailing: Padding(
              padding: const EdgeInsets.only(bottom: 16.0),
              child: IconButton(
                icon: const Icon(Icons.logout),
                tooltip: "Cerrar Sesión",
                onPressed: () => context.read<AuthCubit>().logout(),
              ),
            ),
            destinations: visibleItems.map((item) {
              return NavigationRailDestination(
                icon: Icon(item.icon),
                label: Text(item.label),
              );
            }).toList(),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}