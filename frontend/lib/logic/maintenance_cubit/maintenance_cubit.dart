import 'dart:io';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../core/api/api_exception.dart';
import '../../data/repositories/maintenance_repository.dart';
import 'maintenance_state.dart';

class MaintenanceCubit extends Cubit<MaintenanceState> {
  final MaintenanceRepository _repository;

  MaintenanceCubit(this._repository) : super(const MaintenanceState());

  // Carga inicial para Dashboard (Admin/Mantenimiento)
  Future<void> loadDashboardData() async {
    emit(state.copyWith(
      status: MaintenanceStatus.loading,
      errorMessage: null,
      successMessage: null,
    ));
    try {
      final inc = await _repository.getIncidencias();
      final rep = await _repository.getReparaciones();
      emit(state.copyWith(
        status: MaintenanceStatus.success,
        incidencias: inc,
        reparaciones: rep,
      ));
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error cargando datos'));
    }
  }

  // Acción Técnico: Reportar
  Future<void> reportarIncidencia(int equipoId, String titulo, String descripcion) async {
    emit(state.copyWith(status: MaintenanceStatus.loading, errorMessage: null, successMessage: null));
    try {
      await _repository.reportarIncidencia(equipoId, titulo, descripcion);
      emit(state.copyWith(
        status: MaintenanceStatus.success,
        successMessage: 'Incidencia creada correctamente',
      ));
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error al reportar incidencia'));
    }
  }

  // Acción Admin: Subir Factura
  Future<void> subirFactura(int reparacionId, File file) async {
    emit(state.copyWith(status: MaintenanceStatus.loading, errorMessage: null, successMessage: null));
    try {
      await _repository.subirFactura(reparacionId, file);
      emit(state.copyWith(
        status: MaintenanceStatus.success,
        successMessage: 'Factura subida correctamente',
      ));
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error subiendo archivo'));
    }
  }
}