import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';
import 'package:go_router/go_router.dart'; 

import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../logic/inventory_cubit/inventory_state.dart';
import '../../../../data/models/equipo_model.dart';
import 'equipment_detail_dialog.dart'; // IMPORTANTE

class InventoryGridScreen extends StatefulWidget {
  const InventoryGridScreen({super.key});

  @override
  State<InventoryGridScreen> createState() => _InventoryGridScreenState();
}

class _InventoryGridScreenState extends State<InventoryGridScreen> {
  late List<PlutoColumn> columns;
  bool _isFirstLoad = true;

  @override
  void initState() {
    super.initState();
    context.read<InventoryCubit>().loadInventory();
    _setupColumns();
  }

  void _setupColumns() {
    columns = [
      PlutoColumn(title: 'ID', field: 'id', type: PlutoColumnType.number(), width: 80, readOnly: true),
      PlutoColumn(title: 'Identidad', field: 'identidad', type: PlutoColumnType.text()),
      PlutoColumn(title: 'N. Serie', field: 'serial', type: PlutoColumnType.text()),
      PlutoColumn(title: 'Tipo', field: 'tipo', type: PlutoColumnType.text(), width: 120),
      PlutoColumn(
        title: 'Estado',
        field: 'estado',
        type: PlutoColumnType.text(),
        width: 150,
        renderer: (rendererContext) {
          final val = rendererContext.cell.value.toString();
          Color color = Colors.grey;
          if (val == 'OPERATIVO') color = Colors.green;
          if (val == 'MANTENIMIENTO') color = Colors.orange;
          if (val == 'BAJA') color = Colors.red;
          
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: color.withOpacity(0.5)),
            ),
            child: Text(
              val,
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          );
        },
      ),
      // NUEVO: Ubicación por nombre, no ID
      PlutoColumn(
        title: 'Ubicación',
        field: 'ubicacion',
        type: PlutoColumnType.text(),
        width: 180,
      ),
      PlutoColumn(
        title: 'Historial',
        field: 'history',
        type: PlutoColumnType.text(),
        width: 80,
        enableSorting: false,
        enableFilterMenuItem: false,
        renderer: (_) => const Icon(Icons.history, color: Colors.blue),
      ),
      PlutoColumn(
        title: 'Acciones',
        field: 'actions',
        type: PlutoColumnType.text(),
        width: 120,
        enableSorting: false,
        enableFilterMenuItem: false,
        renderer: (ctx) {
          final row = ctx.row;
          final id = row.cells['id']!.value as int;

          return Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                padding: EdgeInsets.zero,
                iconSize: 18,
                tooltip: 'Editar ficha',
                icon: const Icon(Icons.edit),
                onPressed: () {
                  final state = context.read<InventoryCubit>().state;
                  try {
                    final equipo =
                        state.equipos.firstWhere((e) => e.id == id);
                    _openDetailDialog(equipo);
                  } catch (_) {}
                },
              ),
              IconButton(
                padding: EdgeInsets.zero,
                iconSize: 18,
                tooltip: 'Eliminar equipo',
                icon: const Icon(Icons.delete, color: Colors.red),
                onPressed: () => _confirmDeleteEquipo(id),
              ),
            ],
          );
        },
      ),
    ];
  }

  void _openDetailDialog(EquipoModel equipo) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider.value(
        value: context.read<InventoryCubit>(),
        child: EquipmentDetailDialog(equipo: equipo),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BlocConsumer<InventoryCubit, InventoryState>(
        listener: (context, state) {
          if (state.status == InventoryStatus.failure) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.errorMessage ?? "Error desconocido"),
                backgroundColor: Colors.red,
              ),
            );
          }
        },
        builder: (context, state) {
          if (state.status == InventoryStatus.loading && _isFirstLoad) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state.status == InventoryStatus.success) _isFirstLoad = false;

          if (state.equipos.isEmpty && !_isFirstLoad) {
            return const Center(child: Text("No hay equipos registrados"));
          }

          return PlutoGrid(
            columns: columns,
            rows: state.equipos.map((e) => _buildRow(e, state)).toList(),
            onLoaded: (PlutoGridOnLoadedEvent event) {
              event.stateManager.setShowColumnFilter(true);
            },
            onRowDoubleTap: (event) {
              final id = event.row.cells['id']!.value as int;
              try {
                final equipo = state.equipos.firstWhere((e) => e.id == id);
                _openDetailDialog(equipo);
              } catch (_) {}
            },
            onSelected: (event) {
              final row = event.row;
              if (row != null && event.cell?.column.field == 'history') {
                final id = row.cells['id']!.value;
                context.push('/equipment/$id');
              }
            },
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
    );
  }

  PlutoRow _buildRow(EquipoModel e, InventoryState state) {
    final ubicId = e.ubicacionId;
    final ubicNombre = ubicId != null
        ? (state.ubicaciones[ubicId] ?? 'ID $ubicId')
        : '-';

    return PlutoRow(
      cells: {
        'id': PlutoCell(value: e.id),
        'identidad': PlutoCell(value: e.identidad ?? '-'),
        'serial': PlutoCell(value: e.numeroSerie ?? '-'),
        'tipo': PlutoCell(value: e.tipo),
        'estado': PlutoCell(value: e.estado),
        'ubicacion': PlutoCell(value: ubicNombre),
        'history': PlutoCell(value: 'ver'),
         'actions': PlutoCell(value: 'actions'),
      },
    );
  }

  Future<void> _confirmDeleteEquipo(int id) async {
    final invCubit = context.read<InventoryCubit>();
    final state = invCubit.state;

    final equipo =
        state.equipos.firstWhere((e) => e.id == id, orElse: () => throw Exception());

    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminar equipo'),
        content: Text(
          '¿Seguro que quieres eliminar el equipo "${equipo.identidad ?? equipo.id}"?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text(
              'Eliminar',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );

    if (confirm == true) {
      try {
        await invCubit.eliminarEquipo(id);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Equipo eliminado')),
        );
      } catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Error eliminando equipo'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
