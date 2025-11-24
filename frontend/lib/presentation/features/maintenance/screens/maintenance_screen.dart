import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';

import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
import '../../../../logic/maintenance_cubit/maintenance_state.dart';
import '../../../../data/models/incidencia_model.dart';
import '../../../../data/models/reparacion_model.dart';
import 'repair_detail_dialog.dart';

class MaintenanceScreen extends StatefulWidget {
  const MaintenanceScreen({super.key});

  @override
  State<MaintenanceScreen> createState() => _MaintenanceScreenState();
}

class _MaintenanceScreenState extends State<MaintenanceScreen> {
  @override
  void initState() {
    super.initState();
    context.read<MaintenanceCubit>().loadDashboardData();
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text("Panel de Mantenimiento"),
          bottom: const TabBar(
            tabs: [
              Tab(
                icon: Icon(Icons.warning_amber),
                text: "Incidencias Pendientes",
              ),
              Tab(
                icon: Icon(Icons.build_circle_outlined),
                text: "Reparaciones y Facturas",
              ),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () =>
                  context.read<MaintenanceCubit>().loadDashboardData(),
            )
          ],
        ),
        body: BlocConsumer<MaintenanceCubit, MaintenanceState>(
          listener: (context, state) {
            if (state.status == MaintenanceStatus.failure &&
                state.errorMessage != null) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(state.errorMessage!),
                  backgroundColor: Colors.red,
                ),
              );
            }
            if (state.successMessage != null) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(state.successMessage!),
                  backgroundColor: Colors.green,
                ),
              );
            }
          },
          builder: (context, state) {
            if (state.status == MaintenanceStatus.loading &&
                state.incidencias.isEmpty &&
                state.reparaciones.isEmpty) {
              return const Center(child: CircularProgressIndicator());
            }

            return TabBarView(
              children: [
                _IncidenciasGrid(incidencias: state.incidencias),
                _ReparacionesGrid(reparaciones: state.reparaciones),
              ],
            );
          },
        ),
      ),
    );
  }
}

// --- TABLA DE INCIDENCIAS ---
class _IncidenciasGrid extends StatelessWidget {
  final List<IncidenciaModel> incidencias;

  const _IncidenciasGrid({required this.incidencias});

  @override
  Widget build(BuildContext context) {
    if (incidencias.isEmpty) {
      return const Center(child: Text("No hay incidencias registradas"));
    }

    return PlutoGrid(
      columns: [
        PlutoColumn(
          title: 'ID',
          field: 'id',
          type: PlutoColumnType.number(),
          width: 80,
          readOnly: true,
        ),
        PlutoColumn(
          title: 'Equipo ID',
          field: 'equipo',
          type: PlutoColumnType.number(),
          width: 100,
        ),
        PlutoColumn(
          title: 'Título',
          field: 'titulo',
          type: PlutoColumnType.text(),
          width: 220,
        ),
        PlutoColumn(
          title: 'Estado',
          field: 'estado',
          type: PlutoColumnType.text(),
          width: 140,
          renderer: (ctx) {
            final val = ctx.cell.value.toString();
            Color color = Colors.grey;
            if (val == 'ABIERTA') color = Colors.red;
            if (val == 'EN_PROGRESO') color = Colors.orange;
            if (val == 'CERRADA') color = Colors.green;
            return Text(val, style: TextStyle(color: color, fontWeight: FontWeight.bold));
          },
        ),
        PlutoColumn(
          title: 'Fecha',
          field: 'fecha',
          type: PlutoColumnType.text(),
          width: 150,
        ),
      ],
      rows: incidencias
          .map(
            (e) => PlutoRow(
              cells: {
                'id': PlutoCell(value: e.id),
                'equipo': PlutoCell(value: e.equipoId),
                'titulo': PlutoCell(value: e.titulo),
                'estado': PlutoCell(value: e.estado),
                'fecha': PlutoCell(value: e.fecha ?? '-'),
              },
            ),
          )
          .toList(),
      configuration: const PlutoGridConfiguration(
        style: PlutoGridStyleConfig(
          gridBorderColor: Colors.transparent,
        ),
        columnSize: PlutoGridColumnSizeConfig(
          autoSizeMode: PlutoAutoSizeMode.scale,
        ),
      ),
    );
  }
}

// --- TABLA DE REPARACIONES ---
class _ReparacionesGrid extends StatelessWidget {
  final List<ReparacionModel> reparaciones;

  const _ReparacionesGrid({required this.reparaciones});

  @override
  Widget build(BuildContext context) {
    if (reparaciones.isEmpty) {
      return const Center(child: Text("No hay reparaciones registradas"));
    }

    return PlutoGrid(
      columns: [
        PlutoColumn(
          title: 'ID',
          field: 'id',
          type: PlutoColumnType.number(),
          width: 80,
          readOnly: true,
        ),
        PlutoColumn(
          title: 'Equipo ID',
          field: 'equipo',
          type: PlutoColumnType.number(),
          width: 100,
        ),
        PlutoColumn(
          title: 'Título',
          field: 'titulo',
          type: PlutoColumnType.text(),
        ),
        PlutoColumn(
          title: 'Estado',
          field: 'estado',
          type: PlutoColumnType.text(),
          width: 140,
          renderer: (ctx) {
            final val = ctx.cell.value.toString();
            Color color = Colors.grey;
            if (val == 'ABIERTA') color = Colors.red;
            if (val == 'EN_PROCESO') color = Colors.orange;
            if (val == 'CERRADA') color = Colors.green;
            return Text(val, style: TextStyle(color: color, fontWeight: FontWeight.bold));
          },
        ),
        PlutoColumn(
          title: 'Coste',
          field: 'coste',
          type: PlutoColumnType.currency(symbol: '€'),
          width: 130,
        ),
        PlutoColumn(
          title: 'Acciones',
          field: 'actions',
          type: PlutoColumnType.text(),
          width: 110,
          readOnly: true,
          enableSorting: false,
          enableFilterMenuItem: false,
          renderer: (ctx) => const Icon(
            Icons.folder_open,
            color: Colors.blue,
          ),
        ),
      ],
      rows: reparaciones
          .map(
            (e) => PlutoRow(
              cells: {
                'id': PlutoCell(value: e.id),
                'equipo': PlutoCell(value: e.equipoId),
                'titulo': PlutoCell(value: e.titulo),
                'estado': PlutoCell(value: e.estado),
                'coste': PlutoCell(value: e.coste ?? 0),
                'actions': PlutoCell(value: 'abrir'),
              },
            ),
          )
          .toList(),
      
      // --- FIX DE NULABILIDAD ---
      // Usamos una variable intermedia explícitamente nullable (PlutoRow?)
      // para que Dart permita la comprobación '!= null' sin quejas.
      
      onRowDoubleTap: (event) {
        final PlutoRow? row = event.row; 
        if (row != null) {
          _abrirDetalle(context, row);
        }
      },
      onSelected: (event) {
        final PlutoRow? row = event.row;
        if (row != null && event.cell?.column.field == 'actions') {
          _abrirDetalle(context, row);
        }
      },
      // ---------------------------

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
  }

  void _abrirDetalle(BuildContext context, PlutoRow row) {
    final id = row.cells['id']!.value as int;
    final reparacion = reparaciones.firstWhere((r) => r.id == id);

    showDialog(
      context: context,
      builder: (_) => RepairDetailDialog(reparacion: reparacion),
    );
  }
}