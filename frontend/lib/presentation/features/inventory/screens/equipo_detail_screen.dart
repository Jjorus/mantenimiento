// Ruta: frontend/lib/presentation/features/inventory/screens/equipo_detail_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';


import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../data/repositories/movement_repository.dart';
import '../../../../logic/equipment_history_cubit/equipment_history_cubit.dart';
import '../../../../data/models/incidencia_model.dart';
import '../../../../data/models/movimiento_model.dart';
import '../../../../data/models/reparacion_model.dart';

class EquipoDetailScreen extends StatelessWidget {
  final int equipoId;

  const EquipoDetailScreen({super.key, required this.equipoId});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => EquipmentHistoryCubit(
        movRepo: context.read<MovementRepository>(),
        mantRepo: context.read<MaintenanceRepository>(),
      )..loadHistory(equipoId),
      child: Scaffold(
        appBar: AppBar(
          title: Text("Historial Equipo #$equipoId"),
        ),
        body: BlocBuilder<EquipmentHistoryCubit, EquipmentHistoryState>(
          builder: (context, state) {
            if (state.isLoading) {
              return const Center(child: CircularProgressIndicator());
            }
            if (state.errorMessage != null) {
              return Center(child: Text("Error: ${state.errorMessage}"));
            }
            if (state.timelineItems.isEmpty) {
              return const Center(child: Text("Sin historial registrado."));
            }

            return ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: state.timelineItems.length,
              itemBuilder: (context, index) {
                final item = state.timelineItems[index];
                return _buildTimelineItem(context, item, index, state.timelineItems.length);
              },
            );
          },
        ),
      ),
    );
  }

  Widget _buildTimelineItem(BuildContext context, dynamic item, int index, int total) {
    IconData icon;
    Color color;
    String title;
    String subtitle;
    String dateStr;

    if (item is MovimientoModel) {
      icon = Icons.compare_arrows;
      color = Colors.blue;
      title = "Movimiento";
      subtitle = "Hacia ubicación ${item.haciaUbicacionId ?? '?'}\n${item.comentario ?? ''}";
      dateStr = item.fecha ?? "";
    } else if (item is IncidenciaModel) {
      icon = Icons.warning_amber_rounded;
      color = Colors.orange;
      title = "Incidencia: ${item.titulo}";
      subtitle = "Estado: ${item.estado}";
      dateStr = item.fecha ?? "";
    } else if (item is ReparacionModel) {
      icon = Icons.build;
      color = Colors.green;
      title = "Reparación: ${item.titulo}";
      subtitle = "Coste: ${item.coste ?? 0}€";
      dateStr = item.fechaInicio ?? "";
    } else {
      return const SizedBox.shrink();
    }

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(
                _formatDateShort(dateStr),
                textAlign: TextAlign.right,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ),
          ),
          const SizedBox(width: 12),
          
          Column(
            children: [
              Container(
                width: 2,
                height: 16,
                color: index == 0 ? Colors.transparent : Colors.grey.shade300,
              ),
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  shape: BoxShape.circle,
                  border: Border.all(color: color, width: 2),
                ),
                child: Icon(icon, size: 16, color: color),
              ),
              Expanded(
                child: Container(
                  width: 2,
                  color: index == total - 1 ? Colors.transparent : Colors.grey.shade300,
                ),
              ),
            ],
          ),
          const SizedBox(width: 12),

          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 24.0),
              child: Card(
                elevation: 0,
                shape: RoundedRectangleBorder(
                  side: BorderSide(color: Colors.grey.shade200),
                  borderRadius: BorderRadius.circular(12)
                ),
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                      if (subtitle.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
                      ]
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateShort(String iso) {
    if (iso.isEmpty) return "-";
    try {
      final dt = DateTime.parse(iso);
      return "${dt.day}/${dt.month}/${dt.year}";
    } catch (_) {
      return iso;
    }
  }
}