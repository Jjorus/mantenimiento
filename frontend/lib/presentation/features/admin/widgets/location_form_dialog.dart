import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../data/repositories/inventory_repository.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';

class LocationFormDialog extends StatefulWidget {
  const LocationFormDialog({super.key});

  @override
  State<LocationFormDialog> createState() => _LocationFormDialogState();
}

class _LocationFormDialogState extends State<LocationFormDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nombreCtrl = TextEditingController();
  final _seccionCtrl = TextEditingController();
  String _tipoSeleccionado = 'ALMACEN'; // Valor por defecto

  final List<String> _tiposUbicacion = ['ALMACEN', 'LABORATORIO', 'CLIENTE', 'OTRO'];

  @override
  void dispose() {
    _nombreCtrl.dispose();
    _seccionCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final nombre = _nombreCtrl.text.trim();
    final seccionText = _seccionCtrl.text.trim();
    final int? seccionId = seccionText.isEmpty ? null : int.tryParse(seccionText);

    try {
      // Usamos el repositorio directamente ya que crear ubicación devuelve el modelo
      // y el cubit loadInventory lo actualizará después.
      await context.read<InventoryRepository>().crearUbicacion(
        nombre: nombre,
        tipo: _tipoSeleccionado,
        seccionId: seccionId,
      );

      if (!mounted) return;
      // Recargamos el inventario global para que aparezca en la lista
      context.read<InventoryCubit>().loadInventory();
      Navigator.pop(context);
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Ubicación creada correctamente"), backgroundColor: Colors.green),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Error al crear ubicación"), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text("Nueva Ubicación"),
      content: Form(
        key: _formKey,
        child: SizedBox(
          width: 400,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _nombreCtrl,
                decoration: const InputDecoration(labelText: "Nombre de la ubicación"),
                validator: (v) => v == null || v.trim().isEmpty ? "Requerido" : null,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _tipoSeleccionado,
                decoration: const InputDecoration(labelText: "Tipo"),
                items: _tiposUbicacion.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                onChanged: (v) => setState(() => _tipoSeleccionado = v!),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _seccionCtrl,
                decoration: const InputDecoration(labelText: "ID Sección (Opcional)"),
                keyboardType: TextInputType.number,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text("Cancelar"),
        ),
        ElevatedButton(
          onPressed: _submit,
          child: const Text("Crear"),
        ),
      ],
    );
  }
}