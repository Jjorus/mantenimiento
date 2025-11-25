// Ruta: frontend/lib/logic/equipment_history_cubit/equipment_history_cubit.dart
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../data/models/incidencia_model.dart';
import '../../data/models/movimiento_model.dart';
import '../../data/models/reparacion_model.dart';
import '../../data/repositories/maintenance_repository.dart';
import '../../data/repositories/movement_repository.dart';

class EquipmentHistoryState extends Equatable {
  final bool isLoading;
  final String? errorMessage;
  final List<dynamic> timelineItems; 

  const EquipmentHistoryState({
    this.isLoading = false,
    this.errorMessage,
    this.timelineItems = const [],
  });

  @override
  List<Object?> get props => [isLoading, errorMessage, timelineItems];
}

class EquipmentHistoryCubit extends Cubit<EquipmentHistoryState> {
  final MovementRepository _movRepo;
  final MaintenanceRepository _mantRepo;

  EquipmentHistoryCubit({
    required MovementRepository movRepo,
    required MaintenanceRepository mantRepo,
  }) : _movRepo = movRepo, _mantRepo = mantRepo, super(const EquipmentHistoryState());

  Future<void> loadHistory(int equipoId) async {
    emit(const EquipmentHistoryState(isLoading: true));

    try {
      final results = await Future.wait([
        _movRepo.getHistorial(equipoId),
        _mantRepo.getIncidencias(equipoId: equipoId),
        _mantRepo.getReparaciones(equipoId: equipoId),
      ]);

      final movimientos = results[0] as List<MovimientoModel>;
      final incidencias = results[1] as List<IncidenciaModel>;
      final reparaciones = results[2] as List<ReparacionModel>;

      final List<dynamic> allItems = [
        ...movimientos,
        ...incidencias,
        ...reparaciones
      ];

      allItems.sort((a, b) {
        DateTime? dateA = _getDate(a);
        DateTime? dateB = _getDate(b);
        if (dateA == null) return 1;
        if (dateB == null) return -1;
        return dateB.compareTo(dateA);
      });

      emit(EquipmentHistoryState(isLoading: false, timelineItems: allItems));

    } catch (e) {
      emit(EquipmentHistoryState(isLoading: false, errorMessage: e.toString()));
    }
  }

  DateTime? _getDate(dynamic item) {
    if (item is MovimientoModel) return DateTime.tryParse(item.fecha ?? "");
    if (item is IncidenciaModel) return DateTime.tryParse(item.fecha ?? "");
    if (item is ReparacionModel) return DateTime.tryParse(item.fechaInicio ?? "");
    return null;
  }
}