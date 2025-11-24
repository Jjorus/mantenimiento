import 'package:equatable/equatable.dart';
import '../../data/models/equipo_model.dart';

enum InventoryStatus { initial, loading, success, failure }

class InventoryState extends Equatable {
  final InventoryStatus status;
  final List<EquipoModel> equipos;
  final String? errorMessage;

  const InventoryState({
    this.status = InventoryStatus.initial,
    this.equipos = const [],
    this.errorMessage,
  });

  InventoryState copyWith({
    InventoryStatus? status,
    List<EquipoModel>? equipos,
    String? errorMessage,
  }) {
    return InventoryState(
      status: status ?? this.status,
      equipos: equipos ?? this.equipos,
      errorMessage: errorMessage,
    );
  }

  @override
  List<Object?> get props => [status, equipos, errorMessage];
}