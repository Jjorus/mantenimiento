import '../datasources/movement_remote_ds.dart';
import '../models/movimiento_model.dart';

class MovementRepository {
  final MovementRemoteDataSource _remoteDs;

  MovementRepository({required MovementRemoteDataSource remoteDs}) : _remoteDs = remoteDs;

  Future<MovimientoModel> retirarPorNfc(String tag, {String? comentario}) => 
      _remoteDs.retirarParaMiNfc(tag, comentario: comentario);

  Future<MovimientoModel> retirarManual(int equipoId, {String? comentario}) => 
      _remoteDs.retirarParaMiManual(equipoId, comentario: comentario);
}