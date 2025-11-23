import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs}) : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) => _remoteDs.getEquipoByNfc(tag);
  
  // query es opcional para poder traer "todos" si se deja vacío
  Future<List<EquipoModel>> buscarEquipos({String? query}) => 
      _remoteDs.getEquipos(query: query);
}