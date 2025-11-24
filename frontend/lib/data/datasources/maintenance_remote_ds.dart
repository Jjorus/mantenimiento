import 'dart:io';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/dio_client.dart';
import '../models/incidencia_model.dart';
import '../models/reparacion_model.dart';

class MaintenanceRemoteDataSource {
  final DioClient _client;

  MaintenanceRemoteDataSource(this._client);

  // --- INCIDENCIAS ---
  Future<List<IncidenciaModel>> getIncidencias() async {
    final response = await _client.dio.get('/v1/incidencias');
    return (response.data as List)
        .map((e) => IncidenciaModel.fromJson(e))
        .toList();
  }

  Future<void> createIncidencia(int equipoId, String titulo, String? descripcion) async {
    await _client.dio.post(
      '/v1/incidencias',
      data: {
        'equipo_id': equipoId,
        'titulo': titulo,
        'descripcion': descripcion,
      },
    );
  }

  // --- REPARACIONES ---
  Future<List<ReparacionModel>> getReparaciones() async {
    final response = await _client.dio.get('/v1/reparaciones');
    return (response.data as List)
        .map((e) => ReparacionModel.fromJson(e))
        .toList();
  }

  // --- ARCHIVOS (FACTURAS) ---
  Future<void> uploadFactura(int reparacionId, File file) async {
    final fileName = file.path.split('/').last;

    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });

    await _client.dio.post(
      '/v1/reparaciones/$reparacionId/facturas',
      data: formData,
    );
  }

  Future<List<String>> getFacturasURLs(int reparacionId) async {
    final response = await _client.dio.get('/v1/reparaciones/$reparacionId/facturas');
    // Asumimos que el backend devuelve lista de strings (URLs o nombres)
    return List<String>.from(response.data);
  }

  Future<File> downloadFile(String url) async {
    final tempDir = await getTemporaryDirectory();
    // Usamos timestamp para evitar conflictos de nombres si descargas varias veces
    final fileName = "${DateTime.now().millisecondsSinceEpoch}_${url.split('/').last}";
    final savePath = '${tempDir.path}/$fileName';

    await _client.dio.download(
      url,
      savePath,
      options: Options(responseType: ResponseType.bytes),
    );

    return File(savePath);
  }
}