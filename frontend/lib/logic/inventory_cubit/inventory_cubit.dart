//lib/logic/inventory_cubit/inventory_cubit.dart

import 'package:flutter_bloc/flutter_bloc.dart';
import '../../data/repositories/inventory_repository.dart';
import '../../core/api/api_exception.dart';
import 'inventory_state.dart';

class InventoryCubit extends Cubit<InventoryState> {
  final InventoryRepository _repository;

  InventoryCubit(this._repository) : super(const InventoryState());

  Future<void> loadInventory({String? query}) async {
    // FIX: Limpiamos el error al empezar a cargar para mejorar la UX
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
}