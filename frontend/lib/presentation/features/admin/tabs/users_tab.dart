import 'dart:convert';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';

import '../../../../core/services/storage_service.dart';
import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../../../../logic/admin_cubit/admin_state.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../data/models/user_model.dart';
import '../widgets/user_form_dialog.dart';
import '../widgets/user_detail_dialog.dart';

class UsersTab extends StatefulWidget {
  const UsersTab({super.key});

  @override
  State<UsersTab> createState() => _UsersTabState();
}

class _UsersTabState extends State<UsersTab> {
  late final List<PlutoColumn> columns;
  late final StorageService _storageService;
  Timer? _saveDebounce;

  @override
  void initState() {
    super.initState();
    _storageService = const StorageService();

    columns = [
      PlutoColumn(
        title: 'ID',
        field: 'id',
        type: PlutoColumnType.number(),
        width: 50,
        minWidth: 40,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Usuario',
        field: 'username',
        type: PlutoColumnType.text(),
      ),
      PlutoColumn(
        title: 'Nombre',
        field: 'nombre',
        type: PlutoColumnType.text(),
      ),
      PlutoColumn(
        title: 'Apellidos',
        field: 'apellidos',
        type: PlutoColumnType.text(),
      ),
      PlutoColumn(
        title: 'Email',
        field: 'email',
        type: PlutoColumnType.text(),
        width: 220,
      ),
      PlutoColumn(
        title: 'Ubicación',
        field: 'ubicacion',
        type: PlutoColumnType.text(),
        width: 200,
      ),
      PlutoColumn(
        title: 'Rol',
        field: 'rol',
        type: PlutoColumnType.text(),
      ),
      PlutoColumn(
        title: 'Activo',
        field: 'activo',
        type: PlutoColumnType.text(),
        width: 90,
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
                tooltip: 'Editar',
                icon: const Icon(Icons.edit),
                onPressed: () {
                  final user = context
                      .read<AdminCubit>()
                      .state
                      .users
                      .firstWhere((u) => u.id == id);
                  _openUserDialog(user: user);
                },
              ),
              IconButton(
                padding: EdgeInsets.zero,
                iconSize: 18,
                tooltip: 'Eliminar',
                icon: const Icon(Icons.delete, color: Colors.red),
                onPressed: () => _confirmDeleteUser(id),
              ),
            ],
          );
        },
      ),
    ];

    context.read<InventoryCubit>().loadInventory();
  }

  @override
  void dispose() {
    _saveDebounce?.cancel();
    super.dispose();
  }

  void _openUserDialog({UserModel? user}) {
    showDialog<void>(
      context: context,
      builder: (context) => UserFormDialog(user: user),
    );
  }

  void _openDetailDialog(UserModel user) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => UserDetailDialog(user: user),
    );
  }

  void _openCreateDialog() {
    _openUserDialog();
  }

  // --- MÉTODOS DE PERSISTENCIA CORREGIDOS ---

  Future<void> _saveGridState(PlutoGridStateManager stateManager) async {
    if (_saveDebounce?.isActive ?? false) _saveDebounce!.cancel();

    _saveDebounce = Timer(const Duration(milliseconds: 300), () async {
      try {
        final List<String> columnOrder =
            stateManager.columns.map((c) => c.field).toList();
        final Map<String, double> columnWidths = {
          for (var c in stateManager.columns) c.field: c.width
        };

        final data = jsonEncode({
          'order': columnOrder,
          'widths': columnWidths,
        });

        // OJO: Clave distinta para usuarios
        await _storageService.saveData('users_grid_config', data);
        debugPrint("✅ Configuración de Usuarios guardada: $data");
      } catch (e) {
        debugPrint("❌ Error guardando grid usuarios: $e");
      }
    });
  }

  Future<void> _restoreGridState(PlutoGridStateManager stateManager) async {
    final dataStr = await _storageService.readData('users_grid_config');
    if (dataStr == null) return;

    try {
      final data = jsonDecode(dataStr);
      final Map<String, dynamic> widths = data['widths'];
      final List<dynamic> order = data['order'];

      // 1. Restaurar ANCHOS (Directo)
      for (var col in stateManager.columns) {
        if (widths.containsKey(col.field)) {
          final double savedWidth = (widths[col.field] as num).toDouble();
          col.width = savedWidth;
        }
      }

      // 2. Restaurar ORDEN
      for (int i = 0; i < order.length; i++) {
        final field = order[i];
        final col = stateManager.columns.firstWhere(
            (c) => c.field == field,
            orElse: () => stateManager.columns[0]);

        final currentIndex = stateManager.columns.indexOf(col);

        if (currentIndex != i) {
          final targetCol = stateManager.columns[i];
          stateManager.moveColumn(column: col, targetColumn: targetCol);
        }
      }
      debugPrint("✅ Configuración de Usuarios restaurada correctamente");
    } catch (e) {
      debugPrint("Error restaurando grid de usuarios: $e");
    }
  }

  // --- FIN MÉTODOS DE PERSISTENCIA ---

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AdminCubit, AdminState>(
      listener: (context, state) {},
      builder: (context, state) {
        if (state.status == AdminStatus.loading) {
          return const Center(child: CircularProgressIndicator());
        }

        final invState = context.watch<InventoryCubit>().state;
        final mapaUbicaciones = invState.ubicaciones;

        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 8,
              ),
              child: Row(
                children: [
                  const Text(
                    'Gestión de usuarios',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  ElevatedButton.icon(
                    onPressed: _openCreateDialog,
                    icon: const Icon(Icons.person_add),
                    label: const Text('Nuevo usuario'),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: PlutoGrid(
                columns: columns,
                rows: state.users.map((u) {
                  final ubicId = u.ubicacionId;
                  final ubicNombre = ubicId != null
                      ? (mapaUbicaciones[ubicId] ?? 'ID $ubicId')
                      : '-';

                  return PlutoRow(
                    cells: {
                      'id': PlutoCell(value: u.id),
                      'username': PlutoCell(value: u.username),
                      'nombre': PlutoCell(value: u.nombre ?? ''),
                      'apellidos': PlutoCell(value: u.apellidos ?? ''),
                      'email': PlutoCell(value: u.email),
                      'ubicacion': PlutoCell(value: ubicNombre),
                      'rol': PlutoCell(value: u.role),
                      'activo': PlutoCell(value: u.active ? 'SÍ' : 'NO'),
                      'actions': PlutoCell(value: 'edit'),
                    },
                  );
                }).toList(),
                onRowDoubleTap: (event) {
                  final id = event.row.cells['id']!.value as int;
                  final user =
                      state.users.firstWhere((u) => u.id == id);
                  _openDetailDialog(user);
                },
                onLoaded: (PlutoGridOnLoadedEvent event) {
                  event.stateManager.setShowColumnFilter(true);
                  _restoreGridState(event.stateManager);
                  event.stateManager.addListener(() {
                    _saveGridState(event.stateManager);
                  });
                },
                configuration: const PlutoGridConfiguration(
                  columnSize: PlutoGridColumnSizeConfig(
                    autoSizeMode: PlutoAutoSizeMode.scale,
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _confirmDeleteUser(int id) async {
    final adminCubit = context.read<AdminCubit>();
    final user =
        adminCubit.state.users.firstWhere((u) => u.id == id);

    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminar usuario'),
        content: Text(
          '¿Seguro que quieres eliminar al usuario "${user.username}"?',
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
        await adminCubit.eliminarUsuario(id);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Usuario eliminado')),
        );
      } catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Error eliminando usuario'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}