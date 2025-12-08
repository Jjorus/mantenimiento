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

// 1. Definimos los estados posibles
const List<String> _estadosEquipo = [
  'OPERATIVO',
  'MANTENIMIENTO',
  'BAJA',
  'CALIBRACION',
  'RESERVA'
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
  // 2. Variable para el estado seleccionado
  late String _estadoSeleccionado;

  int? _selectedUbicacionId;

  bool get _isEditing => widget.equipo != null;

  @override
  void initState() {
    super.initState();
    final equipo = widget.equipo;
    _idCtrl = TextEditingController(text: equipo?.identidad ?? '');
    _snCtrl = TextEditingController(text: equipo?.numeroSerie ?? '');
    _nfcCtrl = TextEditingController(text: equipo?.nfcTag ?? '');

    // Campo de texto SOLO para nueva ubicación (lo dejamos vacío)
    _ubicacionCtrl = TextEditingController();
    // Si estamos editando, preseleccionamos la ubicación actual en el desplegable
    _selectedUbicacionId = equipo?.ubicacionId;

    _seccionCtrl =
        TextEditingController(text: equipo?.seccionId?.toString() ?? '');
    _notasCtrl = TextEditingController(text: equipo?.notas ?? '');
    
    final tipo = equipo?.tipo;
    _tipoSeleccionado =
        (tipo != null && _tiposEquipo.contains(tipo)) ? tipo : null;

    // 3. Inicializamos el estado (Por defecto OPERATIVO si es nuevo)
    _estadoSeleccionado = equipo?.estado ?? 'OPERATIVO';
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

    // Lógica para ubicación con método mixto (desplegable + texto)
    int? ubicacionId = _selectedUbicacionId;

    if (ubicacionId == null && ubiText.isNotEmpty) {
      // Si no hay selección en el desplegable pero sí texto, creamos una ubicación nueva
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
              'Error creando la ubicación inicial. '
              'Si ya existe, selecciona una del desplegable.',
            ),
          ),
        );
        return;
      }
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
      await cubit.actualizarEquipo(
        id: widget.equipo!.id,
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        nfcTag: nfcTag,
        ubicacionId: ubicacionId,
        seccionId: seccionId,
        notas: notas,
        estado: _estadoSeleccionado, // 4. Enviamos el estado seleccionado
      );
    } else {
      await cubit.crearEquipo(
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        nfcTag: nfcTag,
        ubicacionId: ubicacionId,
        seccionId: seccionId,
        notas: notas,
        estado: _estadoSeleccionado, // 4. Enviamos el estado seleccionado
      );
    }

    if (!mounted) return;
    // InventoryCubit ya hace loadInventory() dentro de crear/actualizarEquipo,
    // así que las tablas se refrescan solas.
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    // Mapa de ubicaciones desde InventoryCubit para el desplegable
    final invState = context.watch<InventoryCubit>().state;
    final ubicacionesEntries = invState.ubicaciones.entries.toList()
      ..sort((a, b) => a.value.compareTo(b.value));

    final int? selectedUbicValue =
        ubicacionesEntries.any((e) => e.key == _selectedUbicacionId)
            ? _selectedUbicacionId
            : null;

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
                      v == null || v.trim().isEmpty ? "Requerido" : null,
                ),
                const SizedBox(height: 10),
                
                TextFormField(
                  controller: _snCtrl,
                  decoration: const InputDecoration(
                    labelText: "Número de serie",
                  ),
                ),
                const SizedBox(height: 10),
                
                DropdownButtonFormField<String>(
                  initialValue: _tipoSeleccionado,
                  decoration:
                      const InputDecoration(labelText: "Tipo de equipo"),
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

                // 5. NUEVO: Desplegable de ESTADO
                DropdownButtonFormField<String>(
                  value: _estadoSeleccionado,
                  decoration: const InputDecoration(
                    labelText: "Estado actual",
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  ),
                  dropdownColor: Colors.white,
                  items: _estadosEquipo.map((e) {
                    Color color = Colors.black;
                    if(e == 'OPERATIVO') color = Colors.green;
                    if(e == 'MANTENIMIENTO') color = Colors.orange;
                    if(e == 'BAJA') color = Colors.red;
                    
                    return DropdownMenuItem(
                      value: e,
                      child: Text(
                        e, 
                        style: TextStyle(color: color, fontWeight: FontWeight.bold)
                      ),
                    );
                  }).toList(),
                  onChanged: (v) {
                    if (v != null) setState(() => _estadoSeleccionado = v);
                  },
                ),
                const SizedBox(height: 10),

                TextFormField(
                  controller: _nfcCtrl,
                  decoration: const InputDecoration(
                    labelText: "NFC Tag (opcional)",
                  ),
                ),
                const SizedBox(height: 10),

                // Campo de texto para NUEVA ubicación
                TextFormField(
                  controller: _ubicacionCtrl,
                  decoration: const InputDecoration(
                    labelText: "Nueva ubicación inicial",
                    helperText:
                        "Déjalo vacío si quieres usar una ubicación existente",
                  ),
                  keyboardType: TextInputType.text,
                ),
                const SizedBox(height: 10),

                // Desplegable para ubicaciones EXISTENTES
                DropdownButtonFormField<int>(
                  initialValue: selectedUbicValue,
                  decoration: const InputDecoration(
                    labelText: "Ubicación existente",
                    helperText: "Selecciona una ubicación ya creada",
                  ),
                  items: ubicacionesEntries
                      .map(
                        (e) => DropdownMenuItem<int>(
                          value: e.key,
                          child: Text('${e.value} (ID ${e.key})'),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    setState(() {
                      _selectedUbicacionId = value;
                    });
                  },
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