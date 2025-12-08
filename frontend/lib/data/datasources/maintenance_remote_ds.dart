import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/dio_client.dart';
import '../models/incidencia_model.dart';
import '../models/reparacion_model.dart';

class MaintenanceRemoteDataSource {
  final DioClient _client;

  MaintenanceRemoteDataSource(this._client);

  // ---------------------------------------------------------------------------
  // INCIDENCIAS
  // ---------------------------------------------------------------------------

  Future<List<IncidenciaModel>> getIncidencias({
    int? equipoId,
    String? estado,
  }) async {
    final response = await _client.dio.get(
      '/v1/incidencias',
      queryParameters: {
        if (equipoId != null) 'equipo_id': equipoId,
        if (estado != null && estado.isNotEmpty) 'estado': estado,
      },
    );

    return (response.data as List)
        .map((e) => IncidenciaModel.fromJson(e))
        .toList();
  }

  Future<void> createIncidencia({
    required int equipoId,
    required String titulo,
    String? descripcion,
  }) async {
    await _client.dio.post(
      '/v1/incidencias',
      data: {
        'equipo_id': equipoId,
        'titulo': titulo,
        if (descripcion != null && descripcion.isNotEmpty)
          'descripcion': descripcion,
      },
    );
  }

  Future<void> updateIncidencia(
    int id, {
    String? descripcion,
    String? estado,
  }) async {
    final data = <String, dynamic>{};
    if (descripcion != null) data['descripcion'] = descripcion;
    if (estado != null) data['estado'] = estado;

    if (data.isEmpty) return;

    await _client.dio.patch(
      '/v1/incidencias/$id',
      data: data,
    );
  }

  // --- Adjuntos de incidencias ------------------------------------------------

  Future<void> uploadAdjuntoIncidencia(int incidenciaId, File file) async {
    final fileName = file.path.split(Platform.pathSeparator).last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        file.path,
        filename: fileName,
      ),
    });

    await _client.dio.post(
      '/v1/incidencias/$incidenciaId/adjuntos',
      data: formData,
    );
  }

  Future<List<Map<String, dynamic>>> getAdjuntosIncidenciaURLs(
      int incidenciaId) async {
    final response =
        await _client.dio.get('/v1/incidencias/$incidenciaId/adjuntos');
    return (response.data as List)
        .map<Map<String, dynamic>>(
            (e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<void> deleteAdjuntoIncidencia(
      int incidenciaId, int adjuntoId) async {
    await _client.dio
        .delete('/v1/incidencias/$incidenciaId/adjuntos/$adjuntoId');
  }

  // ---------------------------------------------------------------------------
  // REPARACIONES
  // ---------------------------------------------------------------------------

  Future<List<ReparacionModel>> getReparaciones({int? equipoId}) async {
    final path = equipoId != null
        ? '/v1/reparaciones/equipo/$equipoId'
        : '/v1/reparaciones';

    final response = await _client.dio.get(path);
    return (response.data as List)
        .map((e) => ReparacionModel.fromJson(e))
        .toList();
  }

  Future<void> createReparacion({
    required int equipoId,
    required int incidenciaId,
    required String titulo,
    String? descripcion,
    double? costeMateriales,
    double? costeManoObra,
  }) async {
    await _client.dio.post(
      '/v1/reparaciones',
      data: {
        'equipo_id': equipoId,
        'incidencia_id': incidenciaId,
        'titulo': titulo,
        if (descripcion != null && descripcion.isNotEmpty)
          'descripcion': descripcion,
        if (costeMateriales != null) 'coste_materiales': costeMateriales,
        if (costeManoObra != null) 'coste_mano_obra': costeManoObra,
      },
    );
  }

  Future<void> updateReparacion(
    int id, {
    String? descripcion,
    String? estado,
  }) async {
    final data = <String, dynamic>{};
    if (descripcion != null) data['descripcion'] = descripcion;
    if (estado != null) data['estado'] = estado;

    if (data.isEmpty) return;

    await _client.dio.patch(
      '/v1/reparaciones/$id',
      data: data,
    );
  }

  Future<void> closeReparacion(int id) async {
    // Endpoint específico para cerrar
    await _client.dio.post('/v1/reparaciones/$id/cerrar', data: {});
  }

  Future<void> reopenReparacion(int id) async {
    // Endpoint específico para reabrir
    await _client.dio.post('/v1/reparaciones/$id/reabrir', data: {});
  }

  // ---------------------------------------------------------------------------
  // FACTURAS REPARACIÓN
  // ---------------------------------------------------------------------------

  Future<void> subirFactura(int reparacionId, File file) async {
    final fileName = file.path.split(Platform.pathSeparator).last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        file.path,
        filename: fileName,
      ),
    });

    await _client.dio.post(
      '/v1/reparaciones/$reparacionId/facturas',
      data: formData,
    );
  }

  Future<List<Map<String, dynamic>>> getFacturasURLs(
      int reparacionId) async {
    final response = await _client.dio
        .get('/v1/reparaciones/$reparacionId/facturas');
    return (response.data as List)
        .map<Map<String, dynamic>>(
            (e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<void> deleteFacturaReparacion(
      int reparacionId, int facturaId) async {
    await _client.dio
        .delete('/v1/reparaciones/$reparacionId/facturas/$facturaId');
  }

  // ---------------------------------------------------------------------------
  // DESCARGAS COMUNES
  // ---------------------------------------------------------------------------

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
}
