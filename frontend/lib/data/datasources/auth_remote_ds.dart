
import '../../core/api/dio_client.dart';
import '../models/user_model.dart';

class AuthRemoteDataSource {
  final DioClient _client;

  AuthRemoteDataSource(this._client);

  // Login: Ruta backend /api/auth/login
  // (Como base_url es .../api, aquí ponemos /auth/login)
  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await _client.dio.post(
      '/auth/login', 
      data: {
        'username_or_email': username, // Clave exacta que espera tu Pydantic
        'password': password,
      },
    );
    // Devuelve { "access_token": "...", ... }
    return response.data; 
  }

  // Perfil: Ruta backend /api/v1/usuarios/me
  // (Como base_url es .../api, aquí ponemos /v1/usuarios/me)
  Future<UserModel> getUserProfile() async {
    final response = await _client.dio.get('/v1/usuarios/me');
    return UserModel.fromJson(response.data);
  }
}