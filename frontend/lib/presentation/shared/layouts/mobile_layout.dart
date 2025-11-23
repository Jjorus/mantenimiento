import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../logic/auth_cubit/auth_cubit.dart'; // Import Correcto
import 'menu_config.dart';

class MobileLayout extends StatelessWidget {
  final Widget child;
  final String location;

  const MobileLayout({super.key, required this.child, required this.location});

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
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          context.go(visibleItems[index].route);
        },
        destinations: visibleItems.map((item) {
          return NavigationDestination(
            icon: Icon(item.icon),
            label: item.label,
          );
        }).toList(),
      ),
    );
  }
}