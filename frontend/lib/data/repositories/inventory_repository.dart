import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs}) : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) => _remoteDs.getEquipoByNfc(tag);
  
  // FIX: Parámetro con nombre opcional para que coincida con la llamada del Cubit
  Future<List<EquipoModel>> buscarEquipos({String? query}) => 
      _remoteDs.getEquipos(query: query);
}