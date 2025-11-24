import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart'; 

import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../logic/inventory_cubit/inventory_state.dart';
import '../../../../data/models/equipo_model.dart';

class InventoryGridScreen extends StatefulWidget {
  const InventoryGridScreen({super.key});

  @override
  State<InventoryGridScreen> createState() => _InventoryGridScreenState();
}

class _InventoryGridScreenState extends State<InventoryGridScreen> {
  late final List<PlutoColumn> columns;
  bool _isFirstLoad = true;

  @override
  void initState() {
    super.initState();
    context.read<InventoryCubit>().loadInventory();
    _setupColumns();
  }

  void _setupColumns() {
    columns = [
      PlutoColumn(
        title: 'ID',
        field: 'id',
        type: PlutoColumnType.number(),
        width: 80,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Identidad',
        field: 'identidad',
        type: PlutoColumnType.text(),
      ),
      PlutoColumn(
        title: 'N. Serie',
        field: 'serial',
        type: PlutoColumnType.text(),
      ),
      PlutoColumn(
        title: 'Tipo',
        field: 'tipo',
        type: PlutoColumnType.text(),
        width: 120,
      ),
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
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12),
            ),
          );
        },
      ),
      PlutoColumn(
        title: 'Ubicación ID',
        field: 'ubicacion',
        type: PlutoColumnType.number(),
        width: 100,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Inventario Global"),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: "Recargar datos",
            onPressed: () => context.read<InventoryCubit>().loadInventory(),
          ),
        ],
      ),
      body: BlocConsumer<InventoryCubit, InventoryState>(
        listener: (context, state) {
          if (state.status == InventoryStatus.failure) {
            // FIX: Si falla, también quitamos el spinner inicial para mostrar mensaje
            if (_isFirstLoad) setState(() => _isFirstLoad = false);
            
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.errorMessage ?? "Error desconocido"), 
                backgroundColor: Colors.red
              ),
            );
          }
        },
        builder: (context, state) {
          // Loading inicial
          if (state.status == InventoryStatus.loading && _isFirstLoad) {
            return const Center(child: CircularProgressIndicator());
          }

          if (state.status == InventoryStatus.success) _isFirstLoad = false;

          if (state.equipos.isEmpty && !_isFirstLoad) {
             return Center(
               child: Column(
                 mainAxisAlignment: MainAxisAlignment.center,
                 children: [
                   const Icon(Icons.inbox, size: 64, color: Colors.grey),
                   const SizedBox(height: 16),
                   Text("No hay equipos registrados", style: Theme.of(context).textTheme.titleMedium),
                 ],
               ),
             );
          }

          return PlutoGrid(
            columns: columns,
            rows: state.equipos.map((e) => _buildRow(e)).toList(),
            onLoaded: (PlutoGridOnLoadedEvent event) {
              event.stateManager.setShowColumnFilter(true);
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

  PlutoRow _buildRow(EquipoModel e) {
    return PlutoRow(
      cells: {
        'id': PlutoCell(value: e.id),
        'identidad': PlutoCell(value: e.identidad ?? '-'),
        'serial': PlutoCell(value: e.numeroSerie ?? '-'),
        'tipo': PlutoCell(value: e.tipo),
        'estado': PlutoCell(value: e.estado),
        'ubicacion': PlutoCell(value: e.ubicacionId ?? 0),
      },
    );
  }
}