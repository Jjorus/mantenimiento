import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pluto_grid/pluto_grid.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../logic/inventory_cubit/inventory_state.dart';

class LocationDetailDialog extends StatelessWidget {
  final int ubicacionId;
  final String nombreUbicacion;

  const LocationDetailDialog({
    super.key,
    required this.ubicacionId,
    required this.nombreUbicacion,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SizedBox(
        width: 800,
        height: 600,
        child: Column(
          children: [
            // Cabecera
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  const Icon(Icons.place, color: Colors.indigo, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Detalle de Ubicación", style: Theme.of(context).textTheme.titleLarge),
                        Text("$nombreUbicacion (ID: $ubicacionId)", style: const TextStyle(color: Colors.grey)),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  )
                ],
              ),
            ),
            const Divider(height: 1),
            // Cuerpo: Grid de equipos asignados
            Expanded(
              child: BlocBuilder<InventoryCubit, InventoryState>(
                builder: (context, state) {
                  // Filtramos los equipos que pertenecen a esta ubicación
                  final equiposEnUbicacion = state.equipos.where((e) => e.ubicacionId == ubicacionId).toList();

                  if (equiposEnUbicacion.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey.shade300),
                          const SizedBox(height: 16),
                          const Text("No hay equipos asignados a esta ubicación.", style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    );
                  }

                  return Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: PlutoGrid(
                      columns: [
                        PlutoColumn(title: 'ID', field: 'id', type: PlutoColumnType.number(), width: 60, readOnly: true),
                        PlutoColumn(title: 'Identidad', field: 'identidad', type: PlutoColumnType.text(), width: 150),
                        PlutoColumn(title: 'N. Serie', field: 'serial', type: PlutoColumnType.text(), width: 150),
                        PlutoColumn(title: 'Tipo', field: 'tipo', type: PlutoColumnType.text(), width: 120),
                        PlutoColumn(title: 'Estado', field: 'estado', type: PlutoColumnType.text(), width: 120),
                      ],
                      rows: equiposEnUbicacion.map((e) {
                        return PlutoRow(
                          cells: {
                            'id': PlutoCell(value: e.id),
                            'identidad': PlutoCell(value: e.identidad ?? '-'),
                            'serial': PlutoCell(value: e.numeroSerie ?? '-'),
                            'tipo': PlutoCell(value: e.tipo),
                            'estado': PlutoCell(value: e.estado),
                          },
                        );
                      }).toList(),
                      configuration: const PlutoGridConfiguration(
                        style: PlutoGridStyleConfig(
                          gridBorderColor: Colors.transparent,
                          gridBorderRadius: BorderRadius.zero,
                        ),
                        columnSize: PlutoGridColumnSizeConfig(
                          autoSizeMode: PlutoAutoSizeMode.scale,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}