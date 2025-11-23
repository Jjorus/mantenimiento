import 'package:dio/dio.dart';
import '../config/env_config.dart';
import '../services/storage_service.dart';
import 'api_exception.dart';

class DioClient {
  final Dio _dio;
  final StorageService _storageService;

  DioClient(this._storageService)
      : _dio = Dio(
          BaseOptions(
            baseUrl: EnvConfig.apiUrl,
            connectTimeout: Duration(milliseconds: EnvConfig.connectTimeout),
            receiveTimeout: Duration(milliseconds: EnvConfig.receiveTimeout),
            headers: const {'Content-Type': 'application/json'},
          ),
        ) {
    _setupInterceptors();
  }

  Dio get dio => _dio;

  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Inyectar Token si existe
          final token = await _storageService.getToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) async {
          final statusCode = e.response?.statusCode;
          final data = e.response?.data;

          Exception customError;

          switch (statusCode) {
            case 401:
              await _storageService.clearAll();
              customError = AuthException();
              break;
            case 403:
              customError = PermissionException();
              break;
            case 422:
              String msg = "Error de validación";
              if (data is Map && data['detail'] != null) {
                msg = data['detail'].toString();
              }
              customError = ValidationException(msg, data);
              break;
            default:
              customError = ApiException(
                message: e.message ?? "Error de conexión",
                statusCode: statusCode,
                data: data,
              );
          }
          
          return handler.next(DioException(
            requestOptions: e.requestOptions,
            error: customError,
            response: e.response,
            type: e.type,
          )); 
        },
      ),
    );
  }
}