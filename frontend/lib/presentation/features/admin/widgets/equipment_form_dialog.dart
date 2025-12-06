import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/equipo_model.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../data/repositories/inventory_repository.dart';

const List<String> _tiposEquipo = [
// Categorías de equipo
  'Masas',
  'Fuerza',
  'Dimensional',
  '3D',
  'Par',
  'Verificación Dimensional',
  'Temperatura',
  'Electricidad',
  'Químico',
  'Limpieza',
  'Acelerómetros',
  'Acústica',
  'Caudal',
  'Presión',
  'Densidad y Volumen',
  'Óptica y radiometría',
  'Ultrasonidos',

  // Tipos ya existentes en BBDD / backend
  'Calibrador',
  'Multímetro',
  'Generador',
  'Osciloscopio',
  'Fuente',
  'Analizador',
  'Otro',
];

class EquipmentFormDialog extends StatefulWidget {
  final EquipoModel? equipo;

  const EquipmentFormDialog({super.key, this.equipo});

  @override
  State<EquipmentFormDialog> createState() => _EquipmentFormDialogState();
}

class _EquipmentFormDialogState extends State<EquipmentFormDialog> {
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _idCtrl;
  late TextEditingController _snCtrl;
  late TextEditingController _nfcCtrl;
  late TextEditingController _ubicacionCtrl;
  late TextEditingController _seccionCtrl;
  late TextEditingController _notasCtrl;
  String? _tipoSeleccionado;

  bool get _isEditing => widget.equipo != null;

  @override
  void initState() {
    super.initState();
    final equipo = widget.equipo;
    _idCtrl = TextEditingController(text: equipo?.identidad ?? '');
    _snCtrl = TextEditingController(text: equipo?.numeroSerie ?? '');
    _nfcCtrl = TextEditingController(text: equipo?.nfcTag ?? '');
    _ubicacionCtrl =
        TextEditingController(text: equipo?.ubicacionId?.toString() ?? '');
    _seccionCtrl =
        TextEditingController(text: equipo?.seccionId?.toString() ?? '');
    _notasCtrl = TextEditingController(text: equipo?.notas ?? '');
    
    final tipo = equipo?.tipo;
    _tipoSeleccionado =
        (tipo != null && _tiposEquipo.contains(tipo)) ? tipo : null;
  }
  @override
  void dispose() {
    _idCtrl.dispose();
    _snCtrl.dispose();
    _nfcCtrl.dispose();
    _ubicacionCtrl.dispose();
    _seccionCtrl.dispose();
    _notasCtrl.dispose();
    super.dispose();
  }

Future<void> _submit() async {
  if (!_formKey.currentState!.validate()) return;

  final identidad = _idCtrl.text.trim();
  final numeroSerie =
      _snCtrl.text.trim().isEmpty ? null : _snCtrl.text.trim();
  final nfcTag =
      _nfcCtrl.text.trim().isEmpty ? null : _nfcCtrl.text.trim();
  final notas =
      _notasCtrl.text.trim().isEmpty ? null : _notasCtrl.text.trim();

  final ubiText = _ubicacionCtrl.text.trim();
  final secText = _seccionCtrl.text.trim();

  // Igual que antes para sección
  final int? seccionId =
      secText.isEmpty ? null : int.tryParse(secText);

  // NUEVO: lógica para ubicación (ID o nombre)
  int? ubicacionId;
  if (ubiText.isNotEmpty) {
    final parsedId = int.tryParse(ubiText);
    if (parsedId != null) {
      // Si es número, usamos directamente ese ID (como antes)
      ubicacionId = parsedId;
    } else {
      // Si es texto, creamos una ubicación nueva en backend
      try {
        final inventoryRepo = context.read<InventoryRepository>();
        final nuevaUbic = await inventoryRepo.crearUbicacion(
          nombre: ubiText,
          seccionId: seccionId,
          tipo: 'OTRO', // Para equipos: tipo genérico OTRO
        );
        ubicacionId = nuevaUbic.id;
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Error creando la ubicación inicial. Revisa el nombre o inténtalo de nuevo.',
            ),
          ),
        );
        return;
      }
    }
  } else {
    ubicacionId = null;
  }

  final tipo = _tipoSeleccionado;
  if (tipo == null || tipo.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Debes seleccionar un tipo")),
    );
    return;
  }

  final cubit = context.read<InventoryCubit>();

  if (_isEditing) {
    // OJO: mismos parámetros que ya tenías
    await cubit.actualizarEquipo(
      id: widget.equipo!.id,
      identidad: identidad,
      numeroSerie: numeroSerie,
      tipo: tipo,
      nfcTag: nfcTag,
      ubicacionId: ubicacionId,
      seccionId: seccionId,
      notas: notas,
    );
  } else {
    // OJO: mismos parámetros que ya tenías
    await cubit.crearEquipo(
      identidad: identidad,
      numeroSerie: numeroSerie,
      tipo: tipo,
      nfcTag: nfcTag,
      ubicacionId: ubicacionId,
      seccionId: seccionId,
      notas: notas,
    );
  }

  if (!mounted) return;
  Navigator.pop(context);
}


  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title:
          Text(_isEditing ? "Editar ficha de equipo" : "Alta de Nueva Ficha"),
      content: Form(
        key: _formKey,
        child: SizedBox(
          width: 420,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _idCtrl,
                  decoration: const InputDecoration(
                    labelText: "Identidad (ID Interno)",
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? "Requerido" : null,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _snCtrl,
                  decoration: const InputDecoration(
                    labelText: "N. Serie (opcional)",
                  ),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: _tipoSeleccionado,
                  decoration: const InputDecoration(labelText: "Tipo"),
                  items: _tiposEquipo
                      .map(
                        (t) => DropdownMenuItem<String>(
                          value: t,
                          child: Text(t),
                        ),
                      )
                      .toList(),
                  onChanged: (v) => setState(() {
                    _tipoSeleccionado = v;
                  }),
                  validator: (v) =>
                      (v == null || v.isEmpty) ? "Requerido" : null,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _nfcCtrl,
                  decoration: const InputDecoration(
                    labelText: "NFC Tag (opcional)",
                  ),
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _ubicacionCtrl,
                  decoration: const InputDecoration(
                    labelText: "Ubicación ID inicial (ID o nombre)",
                    helperText:
                        "Opcional. Si escribes un nombre, se creara automáticamente",
                  ),
                  keyboardType: TextInputType.text,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _seccionCtrl,
                  decoration: const InputDecoration(
                    labelText: "Sección ID (opcional)",
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _notasCtrl,
                  decoration:
                      const InputDecoration(labelText: "Notas (opcional)"),
                  maxLines: 3,
                ),
              ],
            ),
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
          child: Text(_isEditing ? "Guardar cambios" : "Crear"),
        ),
      ],
    );
  }
}
