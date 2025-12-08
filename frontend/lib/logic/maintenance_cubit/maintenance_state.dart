import 'package:equatable/equatable.dart';
import '../../data/models/incidencia_model.dart';
import '../../data/models/reparacion_model.dart';

enum MaintenanceStatus { initial, loading, success, failure }

class MaintenanceState extends Equatable {
  final MaintenanceStatus status;
  final List<IncidenciaModel> incidencias;
  final List<ReparacionModel> reparaciones;
  final String? errorMessage;
  final String? successMessage;

  const MaintenanceState({
    this.status = MaintenanceStatus.initial,
    this.incidencias = const [],
    this.reparaciones = const [],
    this.errorMessage,
    this.successMessage,
  });

  MaintenanceState copyWith({
    MaintenanceStatus? status,
    List<IncidenciaModel>? incidencias,
    List<ReparacionModel>? reparaciones,
    String? errorMessage,
    String? successMessage,
  }) {
    return MaintenanceState(
      status: status ?? this.status,
      incidencias: incidencias ?? this.incidencias,
      reparaciones: reparaciones ?? this.reparaciones,
      errorMessage: errorMessage, // null limpia el error
      successMessage: successMessage, // null limpia el mensaje
    );
  }

  @override
  List<Object?> get props => [status, incidencias, reparaciones, errorMessage, successMessage];
}