import 'dart:io';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/dio_client.dart';
import '../models/equipo_model.dart';
import '../models/ubicacion_model.dart';

class InventoryRemoteDataSource {
  final DioClient _client;

  InventoryRemoteDataSource(this._client);

  Future<EquipoModel> getEquipoByNfc(String tag) async {
    final response = await _client.dio.get('/v1/equipos/buscar/nfc/$tag');
    return EquipoModel.fromJson(response.data);
  }

  Future<List<EquipoModel>> getEquipos({String? query}) async {
    final response = await _client.dio.get(
      '/v1/equipos',
      queryParameters: {
        if (query != null && query.isNotEmpty) 'q': query,
      },
    );

    return (response.data as List)
        .map((e) => EquipoModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // listar ubicaciones para poder mostrar el nombre
  Future<List<UbicacionModel>> getUbicaciones() async {
    final response = await _client.dio.get(
      '/v1/ubicaciones',
      queryParameters: {
        'limit': 200,
        'offset': 0,
      },
    );

    final dynamic data = response.data;
    List<dynamic> lista;

    if (data is List) {
      // Caso simple: el backend devuelve [ {id, nombre, ...}, ... ]
      lista = data;
    } else if (data is Map<String, dynamic>) {
      // Casos típicos de paginación
      if (data['items'] is List) {
        lista = data['items'] as List;
      } else if (data['results'] is List) {
        lista = data['results'] as List;
      } else if (data['data'] is List) {
        lista = data['data'] as List;
      } else {
        throw Exception(
          'Formato inesperado de /v1/ubicaciones: ${data.runtimeType}',
        );
      }
    } else {
      throw Exception(
        'Respuesta inesperada de /v1/ubicaciones: ${data.runtimeType}',
      );
    }

    return lista
        .where((e) => e != null)
        .map((e) => UbicacionModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // Crear ubicación (se usa desde formularios de usuario/equipo)
  Future<UbicacionModel> crearUbicacion({
    required String nombre,
    int? seccionId,
    String tipo = 'OTRO',
    int? usuarioId,
  }) async {
    final data = <String, dynamic>{
      'nombre': nombre,
      'tipo': tipo,
    };

    if (seccionId != null) {
      data['seccion_id'] = seccionId;
    }
    if (usuarioId != null) {
      data['usuario_id'] = usuarioId;
    }

    try {
      final response = await _client.dio.post(
        '/v1/ubicaciones',
        data: data,
      );
      return UbicacionModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      final detail = e.response?.data;

      // Caso especial: nombre duplicado -> reutilizamos la ubicación existente
      if (statusCode == 422 && detail is List) {
        bool esNombreDuplicado = false;

        for (final err in detail) {
          try {
            final loc = err['loc'];
            final type = err['type']?.toString();
            final msg = err['msg']?.toString() ?? '';

            final locEsNombre =
                loc is List && loc.any((v) => v.toString() == 'nombre');

            if (locEsNombre &&
                (type == 'value_error.unique' ||
                    msg.toLowerCase().contains('ya existe'))) {
              esNombreDuplicado = true;
              break;
            }
          } catch (_) {
            // Ignoramos errores raros en el formato del error
          }
        }

        if (esNombreDuplicado) {
          try {
            // Buscamos la ubicación ya existente con ese nombre
            final todas = await getUbicaciones();
            final buscado = nombre.trim().toLowerCase();
            for (final u in todas) {
              if (u.nombre.trim().toLowerCase() == buscado) {
                return u;
              }
            }
          } catch (_) {
            // Si falla la recarga, dejamos que se repropage el error original
          }
        }
      }

      // Cualquier otro caso (no es nombre duplicado / no pudimos resolverlo)
      rethrow;
    }
  }

  // Crear equipo
  Future<void> createEquipo({
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String estado = 'OPERATIVO',
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) async {
    final data = {
      'identidad': identidad,
      if (numeroSerie != null && numeroSerie.isNotEmpty)
        'numero_serie': numeroSerie,
      'tipo': tipo,
      'estado': estado,
      if (nfcTag != null && nfcTag.isNotEmpty) 'nfc_tag': nfcTag,
      if (seccionId != null) 'seccion_id': seccionId,
      if (ubicacionId != null) 'ubicacion_id': ubicacionId,
      if (notas != null && notas.isNotEmpty) 'notas': notas,
    };

    await _client.dio.post('/v1/equipos', data: data);
  }

  // Actualizar equipo
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
    // FIX: Usar Platform.pathSeparator es más seguro que '/'
    final fileName = file.path.split(Platform.pathSeparator).last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    await _client.dio.post('/v1/equipos/$equipoId/adjuntos', data: formData);
  }

  // FIX CRÍTICO: Devolver Map<String, dynamic> e incluir el 'id'
  // El repositorio necesita el ID para poder borrar el archivo después.
  Future<List<Map<String, dynamic>>> getAdjuntosEquipoURLs(int equipoId) async {
    final response = await _client.dio.get('/v1/equipos/$equipoId/adjuntos');
    
    return (response.data as List).map<Map<String, dynamic>>((e) {
      final map = e as Map<String, dynamic>;
      final idAdjunto = map['id'];
      final nombre = map['nombre_archivo']?.toString() ?? 'archivo';
      
      return {
        'id': idAdjunto, // Importante: pasamos el ID original (int)
        'url': '/v1/equipos/$equipoId/adjuntos/$idAdjunto',
        'fileName': nombre,
        'nombre_archivo': nombre,
        'tipo': map['content_type'] ?? '',
      };
    }).toList();
  }

  Future<File> downloadFile(String url, String fileName) async {
    final tmpDir = await getTemporaryDirectory();
    final savePath = '${tmpDir.path}/$fileName';

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

  Future<void> deleteEquipo(int id) async {
    await _client.dio.delete('/v1/equipos/$id');
  }
}