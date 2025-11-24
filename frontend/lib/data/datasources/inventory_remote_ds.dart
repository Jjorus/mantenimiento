import '../../core/api/dio_client.dart';
import '../models/equipo_model.dart';

class InventoryRemoteDataSource {
  final DioClient _client;

  InventoryRemoteDataSource(this._client);

  // Buscar por NFC
  Future<EquipoModel> getEquipoByNfc(String tag) async {
    final response = await _client.dio.get('/v1/equipos/buscar/nfc/$tag');
    return EquipoModel.fromJson(response.data);
  }

  // Listado general (Parámetros opcionales con nombre)
  Future<List<EquipoModel>> getEquipos({String? query, int? ubicacionId}) async {
    final response = await _client.dio.get(
      '/v1/equipos',
      queryParameters: {
        if (query != null && query.isNotEmpty) 'q': query,
        if (ubicacionId != null) 'ubicacion_id': ubicacionId,
      },
    );
    
    // Backend devuelve lista plana: [ {}, {} ]
    return (response.data as List)
        .map((e) => EquipoModel.fromJson(e))
        .toList();
  }
}