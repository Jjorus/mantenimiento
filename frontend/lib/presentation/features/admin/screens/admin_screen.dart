import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../tabs/users_tab.dart';
import '../tabs/equipment_master_tab.dart';
import '../tabs/database_tab.dart';
import '../tabs/locations_tab.dart'; // <--- IMPORT NUEVO

class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Forzamos la carga inicial de usuarios al entrar
    context.read<AdminCubit>().loadUsers();

    return DefaultTabController(
      length: 4, // <--- CAMBIADO DE 3 A 4
      child: Scaffold(
        appBar: AppBar(
          title: const Text("Administración del Sistema"),
          bottom: const TabBar(
            isScrollable: true, // Recomendado si hay muchas pestañas en móvil
            tabs: [
              Tab(icon: Icon(Icons.people), text: "Gestión Usuarios"),
              Tab(icon: Icon(Icons.inventory), text: "Fichas Equipos"),
              Tab(icon: Icon(Icons.place), text: "Gestor Ubicaciones"), // <--- NUEVA PESTAÑA
              Tab(icon: Icon(Icons.storage), text: "Base de Datos"),
            ],
          ),
        ),
        body: const TabBarView(
          children: [
            UsersTab(),
            EquipmentMasterTab(),
            LocationsTab(), // <--- NUEVO WIDGET
            DatabaseTab(),
          ],
        ),
      ),
    );
  }
}