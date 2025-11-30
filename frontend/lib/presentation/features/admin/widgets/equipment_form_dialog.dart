import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';

class EquipmentFormDialog extends StatefulWidget {
  const EquipmentFormDialog({super.key});

  @override
  State<EquipmentFormDialog> createState() => _EquipmentFormDialogState();
}

class _EquipmentFormDialogState extends State<EquipmentFormDialog> {
  final _formKey = GlobalKey<FormState>();
  final _idCtrl = TextEditingController(); // Identidad
  final _snCtrl = TextEditingController(); // Serie
  final _tipoCtrl = TextEditingController();
  
  void _submit() {
    if (_formKey.currentState!.validate()) {
      // AHORA SÍ: Descomentamos esta parte porque ya existe el método en el Cubit
      context.read<InventoryCubit>().crearEquipo(
        identidad: _idCtrl.text,
        numeroSerie: _snCtrl.text, 
        tipo: _tipoCtrl.text,
      );
      
      Navigator.pop(context);
    }
  }

  @override
  void dispose() {
    _idCtrl.dispose();
    _snCtrl.dispose();
    _tipoCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text("Alta de Nueva Ficha"),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _idCtrl,
              decoration: const InputDecoration(labelText: "Identidad (ID Interno)"),
              validator: (v) => v!.isEmpty ? "Requerido" : null,
            ),
            const SizedBox(height: 10),
            TextFormField(
              controller: _snCtrl, 
              decoration: const InputDecoration(labelText: "N. Serie")
            ),
            const SizedBox(height: 10),
            TextFormField(
              controller: _tipoCtrl, 
              decoration: const InputDecoration(labelText: "Tipo (Multímetro, Calibrador...)"),
              validator: (v) => v!.isEmpty ? "Requerido" : null,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancelar")),
        ElevatedButton(onPressed: _submit, child: const Text("Crear")),
      ],
    );
  }
}