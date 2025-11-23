import '../../core/api/dio_client.dart';
import '../models/movimiento_model.dart';

class MovementRemoteDataSource {
  final DioClient _client;

  MovementRemoteDataSource(this._client);

  // Retirar para mí usando NFC
  Future<MovimientoModel> retirarParaMiNfc(String nfcTag, {String? comentario}) async {
    final response = await _client.dio.post(
      '/v1/movimientos/retirar/me/nfc',
      data: {
        'nfc_tag': nfcTag,
        'comentario': comentario,
      },
    );
    return MovimientoModel.fromJson(response.data);
  }

  // Retirar para mí usando ID (manual)
  Future<MovimientoModel> retirarParaMiManual(int equipoId, {String? comentario}) async {
    final response = await _client.dio.post(
      '/v1/movimientos/retirar/me',
      data: {
        'equipo_id': equipoId,
        'comentario': comentario,
      },
    );
    return MovimientoModel.fromJson(response.data);
  }
}