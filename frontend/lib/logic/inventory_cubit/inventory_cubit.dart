// frontend/lib/logic/inventory_cubit/inventory_cubit.dart
import 'dart:io';

import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/api/api_exception.dart';
import '../../data/repositories/inventory_repository.dart';
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
      // 1) Equipos
      final equipos = await _repository.buscarEquipos(query: query);

      // 2) Ubicaciones → mapa id → nombre
      Map<int, String> mapaUbicaciones = {};
      try {
        final ubicaciones = await _repository.listarUbicaciones();
        mapaUbicaciones = {
          for (final u in ubicaciones) u.id: u.nombre,
        };
      } catch (_) {
        // Si falla, dejamos el mapa vacío y seguimos
        mapaUbicaciones = {};
      }

      emit(
        state.copyWith(
          status: InventoryStatus.success,
          equipos: equipos,
          ubicaciones: mapaUbicaciones,
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
          errorMessage: 'Error inesperado al cargar inventario',
        ),
      );
    }
  }

  Future<void> crearEquipo({
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String estado = 'OPERATIVO',
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) async {
    emit(
      state.copyWith(
        status: InventoryStatus.loading,
        errorMessage: null,
      ),
    );

    try {
      await _repository.crearEquipo(
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        estado: estado,
        nfcTag: nfcTag,
        seccionId: seccionId,
        ubicacionId: ubicacionId,
        notas: notas,
      );
      await loadInventory();
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
          errorMessage: 'Error al crear el equipo',
        ),
      );
      await loadInventory();
    }
  }

  Future<void> actualizarEquipo({
    required int id,
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String? estado,
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) async {
    emit(
      state.copyWith(
        status: InventoryStatus.loading,
        errorMessage: null,
      ),
    );

    try {
      await _repository.actualizarEquipo(
        id: id, // ← aquí con nombre, coincide con tu InventoryRepository
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        estado: estado,
        nfcTag: nfcTag,
        seccionId: seccionId,
        ubicacionId: ubicacionId,
        notas: notas,
      );
      await loadInventory();
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
          errorMessage: 'Error al actualizar el equipo',
        ),
      );
      await loadInventory();
    }
  }

  Future<void> subirAdjuntoEquipo(int equipoId, File file) async {
    try {
      await _repository.subirAdjuntoEquipo(equipoId, file);
    } catch (_) {
      throw Exception('Error al subir adjunto');
    }
  }

  Future<void> eliminarAdjuntoEquipo(int equipoId, int adjuntoId) async {
    try {
      await _repository.eliminarAdjunto(equipoId, adjuntoId);
    } catch (_) {
      throw Exception('Error al eliminar adjunto');
    }
  }

  Future<void> guardarNotas(int equipoId, String notas) async {
    try {
      await _repository.actualizarNotas(equipoId, notas);
      await loadInventory();
    } catch (_) {
      throw Exception('Error guardando notas');
    }
  }

    Future<void> eliminarEquipo(int id) async {
    try {
      await _repository.eliminarEquipo(id);
      await loadInventory();
    } catch (_) {
      throw Exception('Error eliminando equipo');
    }
  }

}
