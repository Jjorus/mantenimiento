// Ruta: frontend/lib/data/datasources/maintenance_remote_ds.dart
// Ruta: frontend/lib/data/datasources/maintenance_remote_ds.dart
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
  
  Future<List<IncidenciaModel>> getIncidencias({
    int? equipoId,
    String? estado,
    String? query,
  }) async {
    final response = await _client.dio.get(
      '/v1/incidencias',
      queryParameters: {
        if (equipoId != null) 'equipo_id': equipoId,
        if (estado != null) 'estado': estado,
        if (query != null) 'q': query,
      },
    );
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

  Future<void> updateIncidenciaEstado(int id, String nuevoEstado) async {
    if (nuevoEstado == 'CERRADA') {
      await _client.dio.post('/v1/incidencias/$id/cerrar');
    } else {
      await _client.dio.patch(
        '/v1/incidencias/$id',
        data: {'estado': nuevoEstado},
      );
    }
  }

  Future<void> updateIncidencia(int id, {String? descripcion}) async {
    await _client.dio.patch(
      '/v1/incidencias/$id',
      data: { if (descripcion != null) 'descripcion': descripcion },
    );
  }

  Future<void> uploadAdjuntoIncidencia(int incidenciaId, File file) async {
    final fileName = file.path.split('/').last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    await _client.dio.post('/v1/incidencias/$incidenciaId/adjuntos', data: formData);
  }

  // CORREGIDO: Devuelve lista de Maps con 'url' y 'fileName'
  Future<List<Map<String, String>>> getAdjuntosIncidenciaURLs(int incidenciaId) async {
    final response = await _client.dio.get('/v1/incidencias/$incidenciaId/adjuntos');
    return (response.data as List).map<Map<String, String>>((e) {
      final idAdjunto = e['id'];
      final nombre = e['nombre_archivo']?.toString() ?? 'archivo'; // Recuperamos nombre
      return {
        'url': '/v1/incidencias/$incidenciaId/adjuntos/$idAdjunto',
        'fileName': nombre
      };
    }).toList();
  }

  // --- REPARACIONES ---
  
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
        'descripcion': descripcion,
        'coste_materiales': costeMateriales,
        'coste_mano_obra': costeManoObra,
        'estado': 'ABIERTA',
      },
    );
  }

  Future<void> updateReparacion(int id, {String? descripcion}) async {
    await _client.dio.patch(
      '/v1/reparaciones/$id',
      data: { if (descripcion != null) 'descripcion': descripcion },
    );
  }

  Future<void> subirFactura(int reparacionId, File file) async {
    final fileName = file.path.split('/').last; 
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    await _client.dio.post('/v1/reparaciones/$reparacionId/factura', data: formData);
  }

  // CORREGIDO: Devuelve lista de Maps con 'url' y 'fileName'
  Future<List<Map<String, String>>> getFacturasURLs(int reparacionId) async {
    final response = await _client.dio.get('/v1/reparaciones/$reparacionId/facturas');
    return (response.data as List).map<Map<String, String>>((e) {
      final idFactura = e['id'];
      final nombre = e['nombre_archivo']?.toString() ?? 'archivo'; // Recuperamos nombre original
      return {
        'url': '/v1/reparaciones/$reparacionId/facturas/$idFactura',
        'fileName': nombre
      };
    }).toList();
  }

  // --- COMÚN ---

  // CORREGIDO: Acepta 'fileName' para preservar extensión
  Future<File> downloadFile(String url, String fileName) async {
    final tempDir = await getTemporaryDirectory();
    // Usamos el nombre original para mantener la extensión (.pdf, .jpg)
    final savePath = '${tempDir.path}/${DateTime.now().millisecondsSinceEpoch}_$fileName';

    await _client.dio.download(
      url,
      savePath,
      options: Options(responseType: ResponseType.bytes),
    );

    return File(savePath);
  }
}