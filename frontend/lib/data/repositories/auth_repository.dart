import 'package:dio/dio.dart';
import '../../core/api/api_exception.dart';
import '../../core/services/storage_service.dart';
import '../datasources/auth_remote_ds.dart';
import '../models/user_model.dart';

class AuthRepository {
  final AuthRemoteDataSource _remoteDs;
  final StorageService _storage;

  AuthRepository({
    required AuthRemoteDataSource remoteDs,
    required StorageService storage,
  })  : _remoteDs = remoteDs,
        _storage = storage;

  Future<UserModel> login(String username, String password) async {
    // 1. Llamada a la API
    final tokens = await _remoteDs.login(username, password);
    
    // 2. Validación y Cast Seguro
    final accessToken = tokens['access_token'] as String?;
    
    // NOTA: Cuando implementes rotación de tokens, descomenta esto:
    // final refreshToken = tokens['refresh_token'] as String?; 

    if (accessToken == null || accessToken.isEmpty) {
      throw ApiException(message: "Error crítico: El servidor no devolvió un token de acceso.");
    }

    // 3. Guardado Seguro
    await _storage.setToken(accessToken);
    
    // TODO: Implementar setRefreshToken en StorageService en el futuro
    // if (refreshToken != null) await _storage.setRefreshToken(refreshToken);

    // 4. Obtener perfil
    return await _remoteDs.getUserProfile();
  }

  Future<void> logout() async {
    await _storage.clearAll();
  }

  Future<UserModel?> checkAuthStatus() async {
    final token = await _storage.getToken();
    if (token == null || token.isEmpty) return null;

    try {
      return await _remoteDs.getUserProfile();
    } catch (e) {
      if (e is AuthException) {
        await _storage.clearAll();
        return null;
      }
      
      if (e is DioException) {
        if (e.response?.statusCode == 401) {
          await _storage.clearAll();
          return null;
        }
        rethrow; 
      }

      await _storage.clearAll();
      return null;
    }
  }
}