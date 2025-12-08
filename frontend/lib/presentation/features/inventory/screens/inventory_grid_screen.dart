import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';
import 'package:go_router/go_router.dart';
import 'dart:convert';
import 'dart:async';

import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../logic/inventory_cubit/inventory_state.dart';
import '../../../../data/models/equipo_model.dart';
import '../../../../core/services/storage_service.dart';
import '../../admin/widgets/equipment_form_dialog.dart';
import 'equipment_detail_dialog.dart';

class InventoryGridScreen extends StatefulWidget {
  // Nuevo parámetro para controlar si mostramos acciones de admin
  final bool isAdminMode;

  const InventoryGridScreen({
    super.key,
    this.isAdminMode = false, // Por defecto oculto (modo lectura)
  });

  @override
  State<InventoryGridScreen> createState() => _InventoryGridScreenState();
}

class _InventoryGridScreenState extends State<InventoryGridScreen> {
  late List<PlutoColumn> columns;
  bool _isFirstLoad = true;
  late final StorageService _storageService;
  Timer? _saveDebounce;

  @override
  void initState() {
    super.initState();
    _storageService = const StorageService();
    context.read<InventoryCubit>().loadInventory();
    _setupColumns();
  }

  @override
  void dispose() {
    _saveDebounce?.cancel();
    super.dispose();
  }

  void _setupColumns() {
    columns = [
      PlutoColumn(title: 'ID', field: 'id', type: PlutoColumnType.number(), width: 50, minWidth: 40, readOnly: true),
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
        width: 140,
        enableSorting: false,
        enableFilterMenuItem: false,
        renderer: (_) => const Icon(Icons.history, color: Colors.blue),
      ),
    ];

    // SOLO añadimos la columna de acciones si estamos en modo Admin
    if (widget.isAdminMode) {
      columns.add(
        PlutoColumn(
          title: 'Acciones',
          field: 'actions',
          type: PlutoColumnType.text(),
          width: 100,
          minWidth: 90,
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
                      final equipo = state.equipos.firstWhere((e) => e.id == id);
                      showDialog(
                        context: context,
                        builder: (_) => BlocProvider.value(
                          value: context.read<InventoryCubit>(),
                          child: EquipmentFormDialog(equipo: equipo),
                        ),
                      );
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
      );
    }
  }

  void _openDetailDialog(EquipoModel equipo) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider.value(
        value: context.read<InventoryCubit>(),
        // Pasamos el modo admin al diálogo de detalle
        child: EquipmentDetailDialog(
          equipo: equipo, 
          isAdminMode: widget.isAdminMode
        ),
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
              
              // Cargar estado guardado
              _restoreGridState(event.stateManager);
              
              // Listener para guardar cambios (debounce reducido a 300ms)
              event.stateManager.addListener(() {
                _saveGridState(event.stateManager);
              });
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

    // Construimos las celdas base
    final cells = {
      'id': PlutoCell(value: e.id),
      'identidad': PlutoCell(value: e.identidad ?? '-'),
      'serial': PlutoCell(value: e.numeroSerie ?? '-'),
      'tipo': PlutoCell(value: e.tipo),
      'estado': PlutoCell(value: e.estado),
      'ubicacion': PlutoCell(value: ubicNombre),
      'history': PlutoCell(value: 'ver'),
    };

    // SOLO añadimos la celda de acciones si es admin
    if (widget.isAdminMode) {
      cells['actions'] = PlutoCell(value: 'actions');
    }

    return PlutoRow(cells: cells);
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

  // --- MÉTODOS DE PERSISTENCIA ---

  Future<void> _saveGridState(PlutoGridStateManager stateManager) async {
    if (_saveDebounce?.isActive ?? false) _saveDebounce!.cancel();

    _saveDebounce = Timer(const Duration(milliseconds: 300), () async {
      try {
        final List<String> columnOrder = stateManager.columns.map((c) => c.field).toList();
        final Map<String, double> columnWidths = {
          for (var c in stateManager.columns) c.field: c.width
        };

        final data = jsonEncode({
          'order': columnOrder,
          'widths': columnWidths,
        });

        await _storageService.saveData('inventory_grid_config', data);
        debugPrint("✅ Configuración de Inventario guardada: $data");
      } catch (e) {
        debugPrint("❌ Error guardando grid inventario: $e");
      }
    });
  }

  Future<void> _restoreGridState(PlutoGridStateManager stateManager) async {
    final dataStr = await _storageService.readData('inventory_grid_config');
    if (dataStr == null) return;

    try {
      final data = jsonDecode(dataStr);
      final Map<String, dynamic> widths = data['widths'];
      final List<dynamic> order = data['order'];

      for (var col in stateManager.columns) {
        if (widths.containsKey(col.field)) {
          final double savedWidth = (widths[col.field] as num).toDouble();
          col.width = savedWidth;
        }
      }

      for (int i = 0; i < order.length; i++) {
        final field = order[i];
        final col = stateManager.columns.firstWhere(
          (c) => c.field == field, 
          orElse: () => stateManager.columns[0]
        );
        
        final currentIndex = stateManager.columns.indexOf(col);
        
        if (currentIndex != i) {
          final targetCol = stateManager.columns[i];
          stateManager.moveColumn(column: col, targetColumn: targetCol);
        }
      }
      debugPrint("✅ Configuración de Inventario restaurada correctamente");

    } catch (e) {
      debugPrint("❌ Error restaurando grid inventario: $e");
    }
  }
}