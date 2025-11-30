import 'dart:io';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../data/repositories/inventory_repository.dart';
import '../../core/api/api_exception.dart';
import 'inventory_state.dart';

class InventoryCubit extends Cubit<InventoryState> {
  final InventoryRepository _repository;

  InventoryCubit(this._repository) : super(const InventoryState());

  Future<void> loadInventory({String? query}) async {
    emit(
      state.copyWith(
        status: InventoryStatus.loading,
        errorMessage: null,
      ),
    );

    try {
      final equipos = await _repository.buscarEquipos(query: query);
      emit(
        state.copyWith(
          status: InventoryStatus.success,
          equipos: equipos,
        ),
      );
    } on ApiException catch (e) {
      emit(
        state.copyWith(
          status: InventoryStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: InventoryStatus.failure,
          errorMessage: "Error inesperado al cargar inventario",
        ),
      );
    }
  }

  // Crear equipo
  Future<void> crearEquipo({
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) async {
    emit(state.copyWith(status: InventoryStatus.loading));
    try {
      await _repository.crearEquipo(
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        nfcTag: nfcTag,
        seccionId: seccionId,
        ubicacionId: ubicacionId,
        notas: notas,
      );
      await loadInventory();
    } catch (_) {
      emit(
        state.copyWith(
          status: InventoryStatus.failure,
          errorMessage: "Error al crear el equipo",
        ),
      );
      loadInventory();
    }
  }

  // Actualizar equipo (edición ficha)
  Future<void> actualizarEquipo({
    required int id,
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) async {
    emit(state.copyWith(status: InventoryStatus.loading));
    try {
      await _repository.actualizarEquipo(
        id: id,
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        nfcTag: nfcTag,
        seccionId: seccionId,
        ubicacionId: ubicacionId,
        notas: notas,
      );
      await loadInventory();
    } catch (_) {
      emit(
        state.copyWith(
          status: InventoryStatus.failure,
          errorMessage: "Error al actualizar el equipo",
        ),
      );
      await loadInventory();
    }
  }

  Future<void> subirAdjuntoEquipo(int equipoId, File file) async {
    try {
      await _repository.subirAdjuntoEquipo(equipoId, file);
    } catch (_) {
      // error silencioso
    }
  }

  Future<void> eliminarAdjuntoEquipo(int equipoId, int adjuntoId) async {
    try {
      await _repository.eliminarAdjunto(equipoId, adjuntoId);
    } catch (_) {
      throw Exception("Error al eliminar adjunto");
    }
  }

  Future<void> guardarNotas(int equipoId, String notas) async {
    try {
      await _repository.actualizarNotas(equipoId, notas);
      loadInventory();
    } catch (_) {
      throw Exception("Error guardando notas");
    }
  }
}
