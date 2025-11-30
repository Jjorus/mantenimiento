import 'dart:io';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/dio_client.dart';
import '../models/equipo_model.dart';

class InventoryRemoteDataSource {
  final DioClient _client;

  InventoryRemoteDataSource(this._client);

  Future<EquipoModel> getEquipoByNfc(String tag) async {
    final response = await _client.dio.get('/v1/equipos/buscar/nfc/$tag');
    return EquipoModel.fromJson(response.data);
  }

  Future<List<EquipoModel>> getEquipos({String? query, int? ubicacionId}) async {
    final response = await _client.dio.get(
      '/v1/equipos',
      queryParameters: {
        if (query != null && query.isNotEmpty) 'q': query,
        if (ubicacionId != null) 'ubicacion_id': ubicacionId,
      },
    );
    return (response.data as List)
        .map((e) => EquipoModel.fromJson(e))
        .toList();
  }

  // Crear equipo
  Future<void> createEquipo(Map<String, dynamic> data) async {
    await _client.dio.post('/v1/equipos', data: data);
  }

  // Actualizar equipo (ficha completa y/o notas)
  Future<void> updateEquipo(
    int id, {
    String? identidad,
    String? numeroSerie,
    String? tipo,
    String? estado,
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) async {
    final data = <String, dynamic>{};
    if (identidad != null) data['identidad'] = identidad;
    if (numeroSerie != null) data['numero_serie'] = numeroSerie;
    if (tipo != null) data['tipo'] = tipo;
    if (estado != null) data['estado'] = estado;
    if (nfcTag != null) data['nfc_tag'] = nfcTag;
    if (seccionId != null) data['seccion_id'] = seccionId;
    if (ubicacionId != null) data['ubicacion_id'] = ubicacionId;
    if (notas != null) data['notas'] = notas;

    if (data.isEmpty) return;

    await _client.dio.patch(
      '/v1/equipos/$id',
      data: data,
    );
  }

  // Adjuntos
  Future<void> uploadAdjuntoEquipo(int equipoId, File file) async {
    final fileName = file.path.split('/').last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    await _client.dio.post('/v1/equipos/$equipoId/adjuntos', data: formData);
  }

  Future<List<Map<String, String>>> getAdjuntosEquipoURLs(int equipoId) async {
    final response = await _client.dio.get('/v1/equipos/$equipoId/adjuntos');
    return (response.data as List).map<Map<String, String>>((e) {
      final idAdjunto = e['id'];
      final nombre = e['nombre_archivo']?.toString() ?? 'archivo';
      return {
        'url': '/v1/equipos/$equipoId/adjuntos/$idAdjunto',
        'fileName': nombre,
      };
    }).toList();
  }

  Future<File> downloadFile(String url, String fileName) async {
    final tempDir = await getTemporaryDirectory();
    final savePath =
        '${tempDir.path}/${DateTime.now().millisecondsSinceEpoch}_$fileName';

    await _client.dio.download(
      url,
      savePath,
      options: Options(responseType: ResponseType.bytes),
    );

    return File(savePath);
  }

  Future<void> deleteAdjuntoEquipo(int equipoId, int adjuntoId) async {
    await _client.dio.delete('/v1/equipos/$equipoId/adjuntos/$adjuntoId');
  }
}
