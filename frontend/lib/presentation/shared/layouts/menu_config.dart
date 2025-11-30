import 'package:flutter/material.dart';

class MenuItem {
  final String route;
  final String label;
  final IconData icon;
  final List<String> allowedRoles; 

  const MenuItem({
    required this.route,
    required this.label,
    required this.icon,
    this.allowedRoles = const [], 
  });
}

const List<MenuItem> appMenuItems = [
  MenuItem(
    route: '/home',
    label: 'Inicio',
    icon: Icons.dashboard_outlined,
  ),
  MenuItem(
    route: '/movement',
    label: 'Escanear',
    icon: Icons.qr_code_scanner,
  ),
  MenuItem(
    route: '/inventory',
    label: 'Inventario',
    icon: Icons.inventory_2_outlined,
  ),
  MenuItem(
    route: '/maintenance',
    label: 'Mantenimiento',
    icon: Icons.build_circle_outlined,
    allowedRoles: ['ADMIN', 'MANTENIMIENTO'],
  ),
  MenuItem(
    route: '/admin',
    label: 'Administración',
    icon: Icons.admin_panel_settings,
    allowedRoles: ['ADMIN'],
  ),
];