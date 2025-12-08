import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../logic/inventory_cubit/inventory_state.dart';
import '../widgets/location_form_dialog.dart';
import '../widgets/location_detail_dialog.dart';

class LocationsTab extends StatefulWidget {
  const LocationsTab({super.key});

  @override
  State<LocationsTab> createState() => _LocationsTabState();
}

class _LocationsTabState extends State<LocationsTab> {
  late final List<PlutoColumn> columns;

  @override
  void initState() {
    super.initState();
    // Aseguramos que los datos estén cargados
    context.read<InventoryCubit>().loadInventory();
    
    columns = [
      PlutoColumn(
        title: 'ID',
        field: 'id',
        type: PlutoColumnType.number(),
        width: 80,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Nombre',
        field: 'nombre',
        type: PlutoColumnType.text(),
        width: 250,
      ),
      PlutoColumn(
        title: 'Acciones',
        field: 'actions',
        type: PlutoColumnType.text(),
        width: 150,
        enableSorting: false,
        enableFilterMenuItem: false,
        renderer: (ctx) {
          final id = ctx.row.cells['id']!.value as int;
          final nombre = ctx.row.cells['nombre']!.value as String;

          return Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Ver equipos asignados
              IconButton(
                icon: const Icon(Icons.visibility, color: Colors.blue),
                tooltip: "Ver equipos asignados",
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (_) => BlocProvider.value(
                      value: context.read<InventoryCubit>(),
                      child: LocationDetailDialog(ubicacionId: id, nombreUbicacion: nombre),
                    ),
                  );
                },
              ),
              const SizedBox(width: 8),
              // Borrar ubicación
              IconButton(
                icon: const Icon(Icons.delete, color: Colors.red),
                tooltip: "Eliminar ubicación",
                onPressed: () => _confirmDelete(id, nombre),
              ),
            ],
          );
        },
      ),
    ];
  }

  void _openCreateDialog() {
    showDialog(
      context: context,
      builder: (_) => BlocProvider.value(
        value: context.read<InventoryCubit>(),
        child: const LocationFormDialog(),
      ),
    );
  }

  Future<void> _confirmDelete(int id, String nombre) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Eliminar Ubicación"),
        content: Text("¿Seguro que deseas eliminar '$nombre'?\n\nSi tiene equipos asignados, la operación fallará."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancelar")),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true), 
            child: const Text("Eliminar", style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      try {
        await context.read<InventoryCubit>().eliminarUbicacion(id);
        if (mounted) {
           ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Ubicación eliminada")));
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString().replaceAll("Exception: ", "")), backgroundColor: Colors.red),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Cabecera estilo Admin
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              const Text(
                'Gestión de Ubicaciones',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              ElevatedButton.icon(
                onPressed: _openCreateDialog,
                icon: const Icon(Icons.add_location_alt),
                label: const Text('Nueva Ubicación'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.indigo,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        
        // Tabla de ubicaciones
        Expanded(
          child: BlocBuilder<InventoryCubit, InventoryState>(
            builder: (context, state) {
              if (state.status == InventoryStatus.loading && state.ubicaciones.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }

              // InventoryState tiene un Map<int, String> ubicaciones.
              // Necesitamos convertirlo a filas para PlutoGrid.
              // Como el mapa solo tiene ID y Nombre, usamos esos datos. 
              // (Si tuviéramos UbicacionModel completo en el estado sería mejor, pero esto sirve para lo básico)
              
              final rows = state.ubicaciones.entries.map((entry) {
                return PlutoRow(
                  cells: {
                    'id': PlutoCell(value: entry.key),
                    'nombre': PlutoCell(value: entry.value),
                    'actions': PlutoCell(value: ''),
                  },
                );
              }).toList();

              // Ordenamos por ID para que no bailen
              rows.sort((a, b) => (a.cells['id']!.value as int).compareTo(b.cells['id']!.value as int));

              return PlutoGrid(
                columns: columns,
                rows: rows,
                configuration: const PlutoGridConfiguration(
                  style: PlutoGridStyleConfig(
                    gridBorderColor: Colors.transparent,
                    gridBorderRadius: BorderRadius.zero,
                  ),
                  columnSize: PlutoGridColumnSizeConfig(
                    autoSizeMode: PlutoAutoSizeMode.scale,
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}