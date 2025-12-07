import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../../data/models/incidencia_model.dart';
import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
import '../../../../logic/maintenance_cubit/maintenance_state.dart';

class RepairFormScreen extends StatefulWidget {
  const RepairFormScreen({super.key});

  @override
  State<RepairFormScreen> createState() => _RepairFormScreenState();
}

class _RepairFormScreenState extends State<RepairFormScreen> {
  final _formKey = GlobalKey<FormState>();
  
  // Campos del formulario
  IncidenciaModel? _selectedIncidencia;
  final _tituloController = TextEditingController();
  final _descController = TextEditingController();
  final _costeMatController = TextEditingController();
  final _costeManoController = TextEditingController();

  // Estado de carga local para las incidencias
  bool _loadingIncidencias = true;
  List<IncidenciaModel> _incidenciasDisponibles = [];
  String? _errorCarga;

  @override
  void initState() {
    super.initState();
    _cargarIncidenciasCandidatas();
  }

  // Cargamos solo incidencias ABIERTA o EN_PROGRESO para vincular
  Future<void> _cargarIncidenciasCandidatas() async {
    try {
      // Usamos el repositorio directamente para no afectar el estado global del dashboard
      final repo = context.read<MaintenanceRepository>();
      // Nota: El backend acepta "estados" separados por coma en el parámetro 'estados' (plural)
      // Si tu repository solo tiene 'estado' (singular), necesitarás llamar dos veces o ajustar el repo.
      // Asumiremos por simplicidad que llamamos a todas y filtramos en memoria o que el repo soporta el filtro.
      // Para ir sobre seguro con tu código actual, pedimos todas las pendientes:
      
      // Opción A: Si tu backend soporta lista en 'estados', úsalo.
      // Opción B (Compatible con tu código actual): Pedimos filtro manual o iterativo.
      // Vamos a pedir TODAS (sin filtro de estado en la API si no está listo) y filtrar aquí, 
      // o pedir una por una. Probemos pidiendo "ABIERTA" y luego "EN_PROGRESO".
      
      final abiertas = await repo.getIncidencias(estado: "ABIERTA");
      final progreso = await repo.getIncidencias(estado: "EN_PROGRESO");
      
      if (mounted) {
        setState(() {
          _incidenciasDisponibles = [...abiertas, ...progreso];
          // Ordenar por fecha descendente
          _incidenciasDisponibles.sort((a, b) => (b.fecha ?? "").compareTo(a.fecha ?? ""));
          _loadingIncidencias = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorCarga = "Error cargando incidencias: $e";
          _loadingIncidencias = false;
        });
      }
    }
  }

  void _submit() {
    if (_formKey.currentState!.validate() && _selectedIncidencia != null) {
      final equipoId = _selectedIncidencia!.equipoId;
      final incidenciaId = _selectedIncidencia!.id;
      
      final mat = double.tryParse(_costeMatController.text);
      final mano = double.tryParse(_costeManoController.text);

      context.read<MaintenanceCubit>().crearReparacion(
        equipoId: equipoId,
        incidenciaId: incidenciaId,
        titulo: _tituloController.text,
        descripcion: _descController.text,
        costeMateriales: mat,
        costeManoObra: mano,
      );
    } else if (_selectedIncidencia == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Debes seleccionar una incidencia base")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Nueva Reparación")),
      body: BlocListener<MaintenanceCubit, MaintenanceState>(
        listener: (context, state) {
          if (state.status == MaintenanceStatus.success) {
            context.pop(); // Volver atrás al terminar
          }
          if (state.status == MaintenanceStatus.failure && state.errorMessage != null) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(state.errorMessage!), backgroundColor: Colors.red),
            );
          }
        },
        child: _loadingIncidencias
            ? const Center(child: CircularProgressIndicator())
            : _errorCarga != null
                ? Center(child: Text(_errorCarga!, style: const TextStyle(color: Colors.red)))
                : SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // SELECCIÓN DE INCIDENCIA
                          Text("Vincular a Incidencia", style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 8),
                          if (_incidenciasDisponibles.isEmpty)
                            const Card(
                              child: Padding(
                                padding: EdgeInsets.all(16.0),
                                child: Text("No hay incidencias abiertas o en progreso para reparar."),
                              ),
                            )
                          else
                            DropdownButtonFormField<IncidenciaModel>(
                              initialValue: _selectedIncidencia,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                              ),
                              hint: const Text("Selecciona una incidencia..."),
                              isExpanded: true,
                              items: _incidenciasDisponibles.map((inc) {
                                return DropdownMenuItem(
                                  value: inc,
                                  child: Text(
                                    "#${inc.id} - ${inc.titulo} (Eq: ${inc.equipoId})",
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                );
                              }).toList(),
                              onChanged: (val) {
                                setState(() {
                                  _selectedIncidencia = val;
                                  // Pre-llenar título si está vacío
                                  if (_tituloController.text.isEmpty && val != null) {
                                    _tituloController.text = "Reparación: ${val.titulo}";
                                  }
                                });
                              },
                            ),
                          
                          const SizedBox(height: 24),
                          
                          // DATOS REPARACIÓN
                          Text("Datos de la Reparación", style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _tituloController,
                            decoration: const InputDecoration(
                              labelText: "Título de la reparación",
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.title),
                            ),
                            validator: (v) => v == null || v.isEmpty ? "Requerido" : null,
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _descController,
                            maxLines: 3,
                            decoration: const InputDecoration(
                              labelText: "Descripción del trabajo",
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.description),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // COSTES
                          Text("Estimación de Costes (Opcional)", style: Theme.of(context).textTheme.titleSmall),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: TextFormField(
                                  controller: _costeMatController,
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  decoration: const InputDecoration(
                                    labelText: "Materiales (€)",
                                    border: OutlineInputBorder(),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: TextFormField(
                                  controller: _costeManoController,
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  decoration: const InputDecoration(
                                    labelText: "Mano de Obra (€)",
                                    border: OutlineInputBorder(),
                                  ),
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 32),
                          
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: FilledButton.icon(
                              onPressed: _incidenciasDisponibles.isEmpty ? null : _submit,
                              icon: const Icon(Icons.save),
                              label: const Text("CREAR REPARACIÓN"),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
      ),
    );
  }
}