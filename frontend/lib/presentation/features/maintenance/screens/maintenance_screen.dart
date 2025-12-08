// Ruta: frontend/lib/presentation/features/maintenance/screens/maintenance_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:pluto_grid/pluto_grid.dart';

import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
import '../../../../logic/maintenance_cubit/maintenance_state.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../data/models/incidencia_model.dart';
import '../../../../data/models/reparacion_model.dart';
import 'repair_detail_dialog.dart';
import 'incident_detail_dialog.dart';
import 'repair_costs_dialog.dart';

class MaintenanceScreen extends StatefulWidget {
  const MaintenanceScreen({super.key});

  @override
  State<MaintenanceScreen> createState() => _MaintenanceScreenState();
}

class _MaintenanceScreenState extends State<MaintenanceScreen> {
  String _filterValue = "TODAS";

  @override
  void initState() {
    super.initState();
    _loadData();
    // Cargamos inventario para tener los nombres de los equipos
    context.read<InventoryCubit>().loadInventory();
  }

  void _loadData() {
    String? estadoBackend;
    if (_filterValue == "PENDIENTES") estadoBackend = "ABIERTA";
    if (_filterValue == "EN PROGRESO") estadoBackend = "EN_PROGRESO";
    if (_filterValue == "CERRADAS") estadoBackend = "CERRADA";

    context
        .read<MaintenanceCubit>()
        .loadDashboardData(filtroEstado: estadoBackend);
  }

  @override
  Widget build(BuildContext context) {
    // Obtenemos mapa de equipos para traducir ID -> Identidad
    final inventoryState = context.watch<InventoryCubit>().state;
    final Map<int, String> equiposMap = {
      for (var e in inventoryState.equipos) e.id: e.identidad ?? 'EQ-${e.id}'
    };

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text("Gestión de Mantenimiento"),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.warning_amber), text: "Incidencias"),
              Tab(icon: Icon(Icons.build_circle_outlined), text: "Reparaciones"),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.add_alert_rounded),
              tooltip: "Nueva Incidencia",
              onPressed: () => context.push('/incidencia/new'),
            ),
            IconButton(
              icon: const Icon(Icons.build),
              tooltip: "Nueva Reparación",
              onPressed: () => context.push('/reparacion/new'),
            ),
            const SizedBox(width: 16),
            DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _filterValue,
                dropdownColor:
                    Theme.of(context).colorScheme.surfaceContainerHighest,
                icon: const Icon(Icons.filter_list),
                items: const [
                  DropdownMenuItem(value: "TODAS", child: Text("Todas")),
                  DropdownMenuItem(value: "PENDIENTES", child: Text("Abiertas")),
                  DropdownMenuItem(value: "EN PROGRESO", child: Text("En Progreso")),
                  DropdownMenuItem(value: "CERRADAS", child: Text("Cerradas")),
                ],
                onChanged: (val) {
                  if (val != null) {
                    setState(() => _filterValue = val);
                    _loadData();
                  }
                },
              ),
            ),
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () {
                _loadData();
                context.read<InventoryCubit>().loadInventory();
              },
            ),
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
                _IncidenciasGrid(
                  key: UniqueKey(),
                  incidencias: state.incidencias,
                  reparaciones: state.reparaciones,
                  equiposMap: equiposMap,
                ),
                _ReparacionesGrid(
                  key: UniqueKey(),
                  reparaciones: state.reparaciones,
                  equiposMap: equiposMap,
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

// ============================================================================
// GRID DE INCIDENCIAS
// ============================================================================

class _IncidenciasGrid extends StatelessWidget {
  final List<IncidenciaModel> incidencias;
  final List<ReparacionModel> reparaciones;
  final Map<int, String> equiposMap;

  const _IncidenciasGrid({
    super.key,
    required this.incidencias,
    required this.reparaciones,
    required this.equiposMap,
  });

  String _formatDateTime(String? iso) {
    if (iso == null || iso.isEmpty) return "-";
    try {
      final dt = DateTime.parse(iso).toLocal();
      return DateFormat('dd/MM/yyyy HH:mm').format(dt);
    } catch (_) {
      return iso;
    }
  }

  void _abrirDetalle(BuildContext context, IncidenciaModel incidencia) {
    showDialog(
      context: context,
      builder: (_) => IncidentDetailDialog(incidencia: incidencia),
    ).then((_) async {
      await Future.delayed(const Duration(milliseconds: 300));
      if (context.mounted) {
        context.read<MaintenanceCubit>().loadDashboardData();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return PlutoGrid(
      columns: [
        PlutoColumn(
          title: 'ID',
          field: 'id',
          type: PlutoColumnType.number(),
          width: 70,
          readOnly: true,
        ),
        PlutoColumn(
          title: 'Equipo',
          field: 'equipo',
          type: PlutoColumnType.text(),
          width: 150,
        ),
        PlutoColumn(
          title: 'Título',
          field: 'titulo',
          type: PlutoColumnType.text(),
          width: 200,
        ),
        PlutoColumn(
          title: 'Estado',
          field: 'estado',
          type: PlutoColumnType.text(),
          width: 120,
          renderer: (ctx) {
            final val = ctx.cell.value.toString();
            Color color = Colors.grey;
            if (val == 'ABIERTA') color = Colors.red;
            if (val == 'EN_PROGRESO') color = Colors.orange;
            if (val == 'CERRADA') color = Colors.green;
            return Chip(
              label: Text(
                val,
                style: const TextStyle(fontSize: 10, color: Colors.white),
              ),
              backgroundColor: color,
              padding: EdgeInsets.zero,
            );
          },
        ),
        PlutoColumn(
          title: 'Reparación',
          field: 'has_repair',
          type: PlutoColumnType.text(),
          width: 100,
          enableSorting: false,
          renderer: (ctx) {
            final hasRepair = ctx.cell.value == 'si';
            return Icon(
              hasRepair ? Icons.build_circle : Icons.highlight_off,
              color: hasRepair
                  ? Colors.green
                  : Colors.grey.withValues(alpha: 0.3),
            );
          },
        ),
        PlutoColumn(
          title: 'Ver',
          field: 'details',
          type: PlutoColumnType.text(),
          width: 80,
          renderer: (ctx) =>
              const Icon(Icons.folder_open, color: Colors.blue),
        ),
        PlutoColumn(
          title: 'Fecha',
          field: 'fecha',
          type: PlutoColumnType.text(),
          width: 160,
        ),
        PlutoColumn(
          title: 'Acciones',
          field: 'actions',
          type: PlutoColumnType.text(),
          width: 190,
          enableSorting: false,
          renderer: (ctx) {
            final estado = ctx.row.cells['estado']!.value.toString();
            final id = ctx.row.cells['id']!.value as int;
            
            final incOriginal = incidencias.firstWhere((i) => i.id == id);
            final equipoId = incOriginal.equipoId;

            if (estado == 'CERRADA') {
              return IconButton(
                icon: const Icon(
                  Icons.add_alert,
                  color: Colors.orange,
                ),
                tooltip: 'Nueva incidencia para este equipo',
                onPressed: () {
                  context.push('/incidencia/new?equipoId=$equipoId');
                },
              );
            }

            return IconButton(
              icon: const Icon(
                Icons.check_circle,
                color: Colors.green,
              ),
              tooltip: 'Cerrar incidencia',
              onPressed: () {
                context
                    .read<MaintenanceCubit>()
                    .cambiarEstadoIncidencia(id, 'CERRADA');
              },
            );
          },
        ),
      ],
      rows: incidencias.map((inc) {
        final tieneRep =
            reparaciones.any((rep) => rep.incidenciaId == inc.id);
        
        final identidad = equiposMap[inc.equipoId] ?? 'ID ${inc.equipoId}';

        return PlutoRow(
          cells: {
            'id': PlutoCell(value: inc.id),
            'equipo': PlutoCell(value: identidad),
            'titulo': PlutoCell(value: inc.titulo),
            'estado': PlutoCell(value: inc.estado),
            'has_repair': PlutoCell(value: tieneRep ? 'si' : 'no'),
            'details': PlutoCell(value: 'abrir'),
            'fecha': PlutoCell(value: _formatDateTime(inc.fecha)),
            'actions': PlutoCell(value: ''),
          },
        );
      }).toList(),
      onRowDoubleTap: (event) {
        final id = event.row.cells['id']!.value as int;
        final inc = incidencias.firstWhere((element) => element.id == id);
        _abrirDetalle(context, inc);
      },
      onSelected: (event) {
        if (event.cell?.column.field == 'details') {
          final id = event.row!.cells['id']!.value as int;
          final inc =
              incidencias.firstWhere((element) => element.id == id);
          _abrirDetalle(context, inc);
        }
      },
      configuration: const PlutoGridConfiguration(
        style: PlutoGridStyleConfig(gridBorderColor: Colors.transparent),
        columnSize: PlutoGridColumnSizeConfig(
          autoSizeMode: PlutoAutoSizeMode.scale,
        ),
      ),
    );
  }
}

// ============================================================================
// GRID DE REPARACIONES
// ============================================================================

class _ReparacionesGrid extends StatelessWidget {
  final List<ReparacionModel> reparaciones;
  final Map<int, String> equiposMap;

  const _ReparacionesGrid({
    super.key,
    required this.reparaciones,
    required this.equiposMap,
  });

  String _formatDateTime(String? iso) {
    if (iso == null || iso.isEmpty) return "-";
    try {
      final dt = DateTime.parse(iso).toLocal();
      return DateFormat('dd/MM/yyyy HH:mm').format(dt);
    } catch (_) {
      return iso;
    }
  }

  Color _colorEstado(String estado) {
    switch (estado) {
      case 'ABIERTA':
        return Colors.red;
      case 'EN_PROGRESO':
        return Colors.orange;
      case 'CERRADA':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  void _abrirDetalle(BuildContext context, PlutoRow row) {
    final id = row.cells['id']!.value as int;
    try {
      final reparacion = reparaciones.firstWhere((r) => r.id == id);
      showDialog(
        context: context,
        builder: (_) => RepairDetailDialog(reparacion: reparacion),
      ).then((_) async {
        await Future.delayed(const Duration(milliseconds: 300));
        if (context.mounted) {
          context.read<MaintenanceCubit>().loadDashboardData();
        }
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Error al abrir detalle")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
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
          title: 'Equipo',
          field: 'equipo',
          type: PlutoColumnType.text(),
          width: 150,
        ),
        PlutoColumn(
          title: 'Incidencia',
          field: 'incidencia',
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
            final raw = ctx.cell.value;
            final val = (raw is String && raw.trim().isNotEmpty)
                ? raw
                : 'ABIERTA';
            final c = _colorEstado(val);
            return Chip(
              label: Text(
                val,
                style: const TextStyle(fontSize: 10, color: Colors.white),
              ),
              backgroundColor: c,
              padding: EdgeInsets.zero,
            );
          },
        ),
        PlutoColumn(
          title: 'Inicio',
          field: 'fecha_inicio',
          type: PlutoColumnType.text(),
          width: 150,
        ),
        PlutoColumn(
          title: 'Fin',
          field: 'fecha_fin',
          type: PlutoColumnType.text(),
          width: 150,
        ),
        PlutoColumn(
          title: 'Coste',
          field: 'coste',
          type: PlutoColumnType.currency(symbol: '€'),
          width: 130,
        ),
        PlutoColumn(
          title: 'Ver',
          field: 'details',
          type: PlutoColumnType.text(),
          width: 80,
          renderer: (ctx) =>
              const Icon(Icons.folder_open, color: Colors.blue),
        ),
        PlutoColumn(
          title: 'Acciones',
          field: 'actions',
          type: PlutoColumnType.text(),
          width: 220,
          enableSorting: false,
          renderer: (ctx) {
            final raw = ctx.row.cells['estado']!.value;
            final estadoActual = (raw is String && raw.trim().isNotEmpty)
                ? raw
                : 'ABIERTA';
            final id = ctx.row.cells['id']!.value as int;

            return Row(
              mainAxisAlignment: MainAxisAlignment.start,
              children: [
                PopupMenuButton<String>(
                  icon: const Icon(Icons.settings, color: Colors.black54),
                  tooltip: 'Cambiar estado',
                  onSelected: (nuevoEstado) {
                    if (nuevoEstado == estadoActual) return;
                    context.read<MaintenanceCubit>().actualizarReparacion(
                      id,
                      estado: nuevoEstado,
                    );
                    ctx.row.cells['estado']!.value = nuevoEstado;
                  },
                  itemBuilder: (context) {
                    return [
                      const PopupMenuItem(
                        value: 'ABIERTA',
                        child: Row(
                          children: [
                            Icon(Icons.lock_open, color: Colors.red, size: 18),
                            SizedBox(width: 8),
                            Text('ABIERTA'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'EN_PROGRESO',
                        child: Row(
                          children: [
                            Icon(Icons.handyman, color: Colors.orange, size: 18),
                            SizedBox(width: 8),
                            Text('EN PROGRESO'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'CERRADA',
                        child: Row(
                          children: [
                            Icon(Icons.check_circle, color: Colors.green, size: 18),
                            SizedBox(width: 8),
                            Text('CERRADA'),
                          ],
                        ),
                      ),
                    ];
                  },
                ),

                // Botón de COSTES (Nuevo)
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.euro_symbol, color: Colors.blueGrey),
                  tooltip: 'Gestionar Costes',
                  onPressed: () {
                    final reparacion = reparaciones.firstWhere((r) => r.id == id);
                    showDialog(
                      context: context,
                      builder: (_) => RepairCostsDialog(reparacion: reparacion),
                    ).then((_) {
                       if (context.mounted) {
                         context.read<MaintenanceCubit>().loadDashboardData();
                       }
                    });
                  },
                ),

                // Botón de Reabrir
                if (estadoActual == 'CERRADA') ...[
                  const SizedBox(width: 4),
                  IconButton(
                    icon: const Icon(Icons.replay, color: Colors.orange),
                    tooltip: 'Reabrir Reparación',
                    onPressed: () {
                      context.read<MaintenanceCubit>().actualizarReparacion(
                        id,
                        estado: 'ABIERTA',
                      );
                      ctx.row.cells['estado']!.value = 'ABIERTA';
                    },
                  ),
                ],
              ],
            );
          },
        ),
      ],
      rows: reparaciones.map((e) {
        final estado = e.estado.trim().isEmpty ? 'ABIERTA' : e.estado;
        final identidad = equiposMap[e.equipoId] ?? 'ID ${e.equipoId}';

        return PlutoRow(
          cells: {
            'id': PlutoCell(value: e.id),
            'equipo': PlutoCell(value: identidad),
            'incidencia': PlutoCell(value: e.incidenciaId ?? 0),
            'titulo': PlutoCell(value: e.titulo),
            'estado': PlutoCell(value: estado),
            'fecha_inicio': PlutoCell(value: _formatDateTime(e.fechaInicio)),
            'fecha_fin': PlutoCell(value: _formatDateTime(e.fechaFin)),
            // CORRECCIÓN: Eliminado '?? 0' porque e.coste ya es double (no nulo)
            'coste': PlutoCell(value: e.coste), 
            'details': PlutoCell(value: 'abrir'),
            'actions': PlutoCell(value: ''),
          },
        );
      }).toList(),
      onRowDoubleTap: (event) => _abrirDetalle(context, event.row),
      onSelected: (event) {
        if (event.cell?.column.field == 'details') {
          _abrirDetalle(context, event.row!);
        }
      },
      configuration: const PlutoGridConfiguration(
        style: PlutoGridStyleConfig(gridBorderColor: Colors.transparent),
        columnSize: PlutoGridColumnSizeConfig(
          autoSizeMode: PlutoAutoSizeMode.scale,
        ),
      ),
    );
  }
}