import 'dart:io';
import 'package:dio/dio.dart';


import '../../core/api/dio_client.dart';
import '../models/user_model.dart';

class AdminRemoteDataSource {
  final DioClient _client;

  AdminRemoteDataSource(this._client);

  // --- USUARIOS ---

  Future<List<UserModel>> getUsers() async {
    final response = await _client.dio.get('/v1/usuarios');
    return (response.data as List).map((e) => UserModel.fromJson(e)).toList();
  }

  Future<void> createUser(Map<String, dynamic> userData) async {
    await _client.dio.post('/v1/usuarios', data: userData);
  }

  Future<void> updateUser(int id, Map<String, dynamic> userData) async {
    await _client.dio.patch('/v1/usuarios/$id', data: userData);
  }

  Future<void> deleteUser(int id) async {
    await _client.dio.delete('/v1/usuarios/$id');
  }

    // --- NOTAS Y ADJUNTOS USUARIO ---

  Future<void> updateNotasUsuario(int id, String notas) async {
    await _client.dio.patch(
      '/v1/usuarios/$id/notas',
      data: {'notas': notas},
    );
  }

  Future<void> uploadAdjuntoUsuario(int userId, File file) async {
    final fileName = file.path.split('/').last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    await _client.dio.post(
      '/v1/usuarios/$userId/adjuntos',
      data: formData,
    );
  }

  Future<List<Map<String, String>>> getAdjuntosUsuarioURLs(int userId) async {
    final response = await _client.dio.get('/v1/usuarios/$userId/adjuntos');
    return (response.data as List).map<Map<String, String>>((e) {
      final idAdjunto = e['id'];
      final nombre = e['nombre_archivo']?.toString() ?? 'archivo';
      return {
        'url': '/v1/usuarios/$userId/adjuntos/$idAdjunto',
        'fileName': nombre,
      };
    }).toList();
  }

  Future<void> deleteAdjuntoUsuario(int userId, int adjuntoId) async {
    await _client.dio
        .delete('/v1/usuarios/$userId/adjuntos/$adjuntoId');
  }

}