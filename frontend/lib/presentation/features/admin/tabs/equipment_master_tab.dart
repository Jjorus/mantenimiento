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
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: const InventoryGridScreen(), // Grid existente
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openCreateDialog(context),
        label: const Text("Alta Equipo"),
        icon: const Icon(Icons.add_box),
        backgroundColor: Colors.orange,
      ),
    );
  }
}