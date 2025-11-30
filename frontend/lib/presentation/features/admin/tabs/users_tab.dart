import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';
import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../../../../logic/admin_cubit/admin_state.dart';
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
      PlutoColumn(title: 'ID', field: 'id', type: PlutoColumnType.number(), width: 80, readOnly: true),
      PlutoColumn(title: 'Usuario', field: 'username', type: PlutoColumnType.text()),
      PlutoColumn(title: 'Nombre', field: 'nombre', type: PlutoColumnType.text()),     // OK
      PlutoColumn(title: 'Apellidos', field: 'apellidos', type: PlutoColumnType.text()), // OK
      PlutoColumn(title: 'Email', field: 'email', type: PlutoColumnType.text(), width: 200),
      PlutoColumn(title: 'Rol', field: 'rol', type: PlutoColumnType.text()),
      PlutoColumn(title: 'Activo', field: 'activo', type: PlutoColumnType.text(), width: 100),
      PlutoColumn(
        title: 'Acciones',
        field: 'actions',
        type: PlutoColumnType.text(),
        renderer: (ctx) => const Icon(Icons.edit, color: Colors.blue),
        width: 100,
        enableSorting: false,
        enableFilterMenuItem: false,
      ),
    ];
  }

  void _openUserDialog({UserModel? user}) {
    showDialog(
      context: context,
      builder: (_) => BlocProvider.value(
        value: context.read<AdminCubit>(),
        child: UserFormDialog(user: user),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openUserDialog(),
        label: const Text("Nuevo Usuario"),
        icon: const Icon(Icons.person_add),
      ),
      body: BlocConsumer<AdminCubit, AdminState>(
        listener: (context, state) {
          if (state.successMessage != null) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(state.successMessage!), backgroundColor: Colors.green));
          }
          if (state.errorMessage != null) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(state.errorMessage!), backgroundColor: Colors.red));
          }
        },
        builder: (context, state) {
          if (state.status == AdminStatus.loading) return const Center(child: CircularProgressIndicator());
          
          return PlutoGrid(
            columns: columns,
            rows: state.users.map((u) => PlutoRow(
              cells: {
                'id': PlutoCell(value: u.id),
                'username': PlutoCell(value: u.username),
                'nombre': PlutoCell(value: u.nombre ?? ""),
                'apellidos': PlutoCell(value: u.apellidos ?? ""),
                'email': PlutoCell(value: u.email),
                'rol': PlutoCell(value: u.role),
                'activo': PlutoCell(value: u.active ? "SÍ" : "NO"),
                'actions': PlutoCell(value: "edit"),
              }
            )).toList(),
            onRowDoubleTap: (event) {
               final id = event.row.cells['id']!.value as int;
               final user = state.users.firstWhere((u) => u.id == id);
               _openUserDialog(user: user);
            },
            configuration: const PlutoGridConfiguration(
              columnSize: PlutoGridColumnSizeConfig(autoSizeMode: PlutoAutoSizeMode.scale),
            ),
          );
        },
      ),
    );
  }
}