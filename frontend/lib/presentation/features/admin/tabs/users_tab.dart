import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';

import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../../../../logic/admin_cubit/admin_state.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../data/models/user_model.dart';
import '../widgets/user_form_dialog.dart';

class UsersTab extends StatefulWidget {
  const UsersTab({super.key});

  @override
  State<UsersTab> createState() => _UsersTabState();
}

class _UsersTabState extends State<UsersTab> {
  late final List<PlutoColumn> columns;

  @override
  void initState() {
    super.initState();

    columns = [
      PlutoColumn(
        title: 'ID',
        field: 'id',
        type: PlutoColumnType.number(),
        width: 80,
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
        width: 110,
        enableSorting: false,
        enableFilterMenuItem: false,
      ),
    ];

    // Cargamos inventario para tener el mapa id → nombre de ubicaciones
    // (el mismo que usa InventoryGridScreen)
    context.read<InventoryCubit>().loadInventory();
  }

  void _openUserDialog({UserModel? user}) {
    showDialog<void>(
      context: context,
      builder: (context) => UserFormDialog(user: user),
    );
  }

  void _openCreateDialog() {
    _openUserDialog();
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AdminCubit, AdminState>(
      listener: (context, state) {
        // Si en tu AdminState tienes errores o mensajes,
        // puedes manejar aquí los SnackBars como antes.
      },
      builder: (context, state) {
        if (state.status == AdminStatus.loading) {
          return const Center(child: CircularProgressIndicator());
        }

        // Mapa id_ubicacion → nombre que viene de InventoryCubit
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
                  _openUserDialog(user: user);
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
}
