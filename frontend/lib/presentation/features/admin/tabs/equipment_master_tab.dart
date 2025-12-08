import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../inventory/screens/inventory_grid_screen.dart'; // Reutilizamos el grid existente
import '../widgets/equipment_form_dialog.dart';

class EquipmentMasterTab extends StatelessWidget {
  const EquipmentMasterTab({super.key});

  void _openCreateDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => BlocProvider.value(
        value: context.read<InventoryCubit>(),
        child: const EquipmentFormDialog(),
      ),
    ).then((_) {
      // CORRECCIÓN: Usar 'mounted' para refrescar de forma segura
      if (context.mounted) {
        context.read<InventoryCubit>().loadInventory();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    // Usamos Column para poner cabecera arriba y la tabla abajo
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              const Text(
                'Gestión de Equipos',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              // Botón estilo "Gestión de usuarios"
              ElevatedButton.icon(
                onPressed: () => _openCreateDialog(context),
                icon: const Icon(Icons.add_box),
                label: const Text('Alta Equipo'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        // La tabla ocupa el resto del espacio
        const Expanded(
          // AQUÍ SE ACTIVA EL MODO ADMIN
          child: InventoryGridScreen(isAdminMode: true), 
        ),
      ],
    );
  }
}