import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../tabs/users_tab.dart';
import '../tabs/equipment_master_tab.dart';
import '../tabs/database_tab.dart';

class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Forzamos la carga inicial de usuarios al entrar
    context.read<AdminCubit>().loadUsers();

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text("Administración del Sistema"),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.people), text: "Gestión Usuarios"),
              Tab(icon: Icon(Icons.inventory), text: "Fichas Equipos"),
              Tab(icon: Icon(Icons.storage), text: "Base de Datos"),
            ],
          ),
        ),
        body: const TabBarView(
          children: [
            UsersTab(),
            EquipmentMasterTab(), // CRUD completo de equipos
            DatabaseTab(),        // Gestión BD
          ],
        ),
      ),
    );
  }
}