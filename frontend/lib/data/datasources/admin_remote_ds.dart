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
}