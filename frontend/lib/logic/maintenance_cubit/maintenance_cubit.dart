import 'dart:io';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../core/api/api_exception.dart';
import '../../data/repositories/maintenance_repository.dart';
import 'maintenance_state.dart';

class MaintenanceCubit extends Cubit<MaintenanceState> {
  final MaintenanceRepository _repository;

  String? _filtroEstado;

  MaintenanceCubit(this._repository) : super(const MaintenanceState());

  Future<void> loadDashboardData({String? filtroEstado}) async {
    _filtroEstado = filtroEstado;
    
    emit(state.copyWith(
      status: MaintenanceStatus.loading,
      errorMessage: null,
      successMessage: null,
    ));
    try {
      final inc = await _repository.getIncidencias(estado: _filtroEstado);
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

  // --- INCIDENCIAS ---

  Future<void> cambiarEstadoIncidencia(int id, String nuevoEstado) async {
    try {
      await _repository.cambiarEstadoIncidencia(id, nuevoEstado);
      emit(state.copyWith(successMessage: "Incidencia actualizada a $nuevoEstado"));
      loadDashboardData(filtroEstado: _filtroEstado);
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error al actualizar incidencia'));
    }
  }

  Future<void> reportarIncidencia(int equipoId, String titulo, String descripcion) async {
    emit(state.copyWith(status: MaintenanceStatus.loading, errorMessage: null, successMessage: null));
    try {
      await _repository.reportarIncidencia(equipoId, titulo, descripcion);
      emit(state.copyWith(status: MaintenanceStatus.success, successMessage: 'Incidencia creada correctamente'));
      loadDashboardData(filtroEstado: _filtroEstado);
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error al reportar incidencia'));
    }
  }

  Future<void> actualizarIncidencia(int id, {String? descripcion}) async {
    try {
      await _repository.actualizarIncidencia(id, descripcion: descripcion);
      emit(state.copyWith(successMessage: "Incidencia actualizada"));
      loadDashboardData(filtroEstado: _filtroEstado);
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error actualizando incidencia'));
    }
  }

  Future<void> subirAdjuntoIncidencia(int id, File file) async {
    emit(state.copyWith(status: MaintenanceStatus.loading, errorMessage: null, successMessage: null));
    try {
      await _repository.subirAdjuntoIncidencia(id, file);
      emit(state.copyWith(status: MaintenanceStatus.success, successMessage: 'Archivo subido correctamente'));
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error subiendo archivo'));
    }
  }

  // NUEVO: Eliminar
  Future<void> eliminarAdjuntoIncidencia(int incidenciaId, int adjuntoId) async {
    try {
      await _repository.eliminarAdjuntoIncidencia(incidenciaId, adjuntoId);
      emit(state.copyWith(successMessage: "Adjunto eliminado"));
    } catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error eliminando adjunto'));
    }
  }


  // --- REPARACIONES ---

  Future<void> crearReparacion({
    required int equipoId,
    required int incidenciaId,
    required String titulo,
    String? descripcion,
    double? costeMateriales,
    double? costeManoObra,
  }) async {
    emit(state.copyWith(status: MaintenanceStatus.loading, errorMessage: null, successMessage: null));
    try {
      await _repository.crearReparacion(
        equipoId: equipoId,
        incidenciaId: incidenciaId,
        titulo: titulo,
        descripcion: descripcion,
        costeMateriales: costeMateriales,
        costeManoObra: costeManoObra,
      );
      emit(state.copyWith(status: MaintenanceStatus.success, successMessage: 'Reparación creada correctamente'));
      loadDashboardData(filtroEstado: _filtroEstado);
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error al crear reparación'));
    }
  }

  Future<void> actualizarReparacion(int id, {String? descripcion}) async {
    try {
      await _repository.actualizarReparacion(id, descripcion: descripcion);
      emit(state.copyWith(successMessage: "Reparación actualizada"));
      loadDashboardData(filtroEstado: _filtroEstado);
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error actualizando reparación'));
    }
  }
  
  Future<void> subirFactura(int reparacionId, File file) async {
    emit(state.copyWith(status: MaintenanceStatus.loading, errorMessage: null, successMessage: null));
    try {
      await _repository.subirFactura(reparacionId, file);
      emit(state.copyWith(status: MaintenanceStatus.success, successMessage: 'Factura subida correctamente'));
    } on ApiException catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: e.message));
    } catch (_) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error subiendo archivo'));
    }
  }

  // NUEVO: Eliminar
  Future<void> eliminarFactura(int reparacionId, int facturaId) async {
    try {
      await _repository.eliminarFactura(reparacionId, facturaId);
      emit(state.copyWith(successMessage: "Factura eliminada"));
    } catch (e) {
      emit(state.copyWith(status: MaintenanceStatus.failure, errorMessage: 'Error eliminando factura'));
    }
  }
}