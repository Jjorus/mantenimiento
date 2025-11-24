import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
import '../../../../logic/maintenance_cubit/maintenance_state.dart';

class IncidentFormScreen extends StatefulWidget {
  final int? equipoId;

  const IncidentFormScreen({super.key, this.equipoId});

  @override
  State<IncidentFormScreen> createState() => _IncidentFormScreenState();
}

class _IncidentFormScreenState extends State<IncidentFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _tituloCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _idCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    if (widget.equipoId != null) {
      _idCtrl.text = widget.equipoId.toString();
    }
  }

  @override
  void dispose() {
    _tituloCtrl.dispose();
    _descCtrl.dispose();
    _idCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    
    // Llamar al Cubit
    context.read<MaintenanceCubit>().reportarIncidencia(
      int.parse(_idCtrl.text),
      _tituloCtrl.text,
      _descCtrl.text,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<MaintenanceCubit, MaintenanceState>(
      listener: (context, state) {
        if (state.status == MaintenanceStatus.success) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Incidencia reportada con éxito"), backgroundColor: Colors.green),
          );
          context.pop(); // Volver atrás
        }
        if (state.status == MaintenanceStatus.failure) {
           ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(state.errorMessage ?? "Error"), backgroundColor: Colors.red),
          );
        }
      },
      child: Scaffold(
        appBar: AppBar(title: const Text("Reportar Avería")),
        body: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: ListView(
              children: [
                TextFormField(
                  controller: _idCtrl,
                  decoration: const InputDecoration(
                    labelText: "ID Equipo",
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.qr_code),
                  ),
                  keyboardType: TextInputType.number,
                  // Si viene pre-rellenado (del escáner), lo bloqueamos para evitar errores
                  enabled: widget.equipoId == null, 
                  validator: (v) => (v?.isEmpty ?? true) ? "Requerido" : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _tituloCtrl,
                  decoration: const InputDecoration(
                    labelText: "Título del problema",
                    hintText: "Ej: Pantalla rota",
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => (v?.isEmpty ?? true) ? "Requerido" : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _descCtrl,
                  decoration: const InputDecoration(
                    labelText: "Descripción detallada",
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 4,
                ),
                const SizedBox(height: 32),
                FilledButton.icon(
                  onPressed: _submit,
                  icon: const Icon(Icons.send),
                  label: const Text("ENVIAR REPORTE"),
                  style: FilledButton.styleFrom(padding: const EdgeInsets.all(16)),
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}