// frontend/lib/logic/inventory_cubit/inventory_state.dart
import 'package:equatable/equatable.dart';
import '../../data/models/equipo_model.dart';

enum InventoryStatus { initial, loading, success, failure }

class InventoryState extends Equatable {
  final InventoryStatus status;
  final List<EquipoModel> equipos;
  final String? errorMessage;

  /// Mapa id_ubicacion → nombre legible
  final Map<int, String> ubicaciones;

  const InventoryState({
    this.status = InventoryStatus.initial,
    this.equipos = const [],
    this.errorMessage,
    this.ubicaciones = const {},
  });

  InventoryState copyWith({
    InventoryStatus? status,
    List<EquipoModel>? equipos,
    String? errorMessage,
    Map<int, String>? ubicaciones,
  }) {
    return InventoryState(
      status: status ?? this.status,
      equipos: equipos ?? this.equipos,
      errorMessage: errorMessage,
      ubicaciones: ubicaciones ?? this.ubicaciones,
    );
  }

  @override
  List<Object?> get props => [status, equipos, errorMessage, ubicaciones];
}
