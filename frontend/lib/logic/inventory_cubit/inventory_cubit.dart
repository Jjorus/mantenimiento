import 'dart:io';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../data/repositories/inventory_repository.dart';
import '../../core/api/api_exception.dart';
import 'inventory_state.dart';

class InventoryCubit extends Cubit<InventoryState> {
  final InventoryRepository _repository;

  InventoryCubit(this._repository) : super(const InventoryState());

  Future<void> loadInventory({String? query}) async {
    emit(state.copyWith(
      status: InventoryStatus.loading, 
      errorMessage: null
    ));
    
    try {
      final equipos = await _repository.buscarEquipos(query: query);
      emit(state.copyWith(
        status: InventoryStatus.success,
        equipos: equipos,
      ));
    } on ApiException catch (e) {
      emit(state.copyWith(
        status: InventoryStatus.failure,
        errorMessage: e.message,
      ));
    } catch (e) {
      emit(state.copyWith(
        status: InventoryStatus.failure,
        errorMessage: "Error inesperado al cargar inventario",
      ));
    }
  }

  // --- NUEVO: Crear Equipo ---
  Future<void> crearEquipo({
    required String identidad,
    String? numeroSerie,
    required String tipo,
  }) async {
    emit(state.copyWith(status: InventoryStatus.loading));
    try {
      await _repository.crearEquipo(
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
      );
      // Recargamos el inventario para mostrar el nuevo equipo
      await loadInventory();
    } catch (e) {
      emit(state.copyWith(
        status: InventoryStatus.failure,
        errorMessage: "Error al crear el equipo",
      ));
      // Volvemos a cargar para restaurar la lista si falló
      loadInventory(); 
    }
  }

  Future<void> subirAdjuntoEquipo(int equipoId, File file) async {
    try {
      await _repository.subirAdjuntoEquipo(equipoId, file);
    } catch (e) {
      // Manejar error silenciosamente o emitir estado temporal
    }
  }

  Future<void> eliminarAdjuntoEquipo(int equipoId, int adjuntoId) async {
    try {
      await _repository.eliminarAdjunto(equipoId, adjuntoId);
    } catch (e) {
      throw Exception("Error al eliminar adjunto");
    }
  }

  Future<void> guardarNotas(int equipoId, String notas) async {
    try {
      await _repository.actualizarNotas(equipoId, notas);
      loadInventory(); 
    } catch (e) {
      throw Exception("Error guardando notas");
    }
  }
}