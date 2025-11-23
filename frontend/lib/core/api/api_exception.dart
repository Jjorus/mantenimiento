class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic data;

  ApiException({
    required this.message, 
    this.statusCode, 
    this.data
  });

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class AuthException extends ApiException {
  AuthException({String message = "Sesión caducada o credenciales inválidas"})
      : super(message: message, statusCode: 401);
}

class PermissionException extends ApiException {
  PermissionException() : super(message: "No tienes permisos para esta acción", statusCode: 403);
}

class ValidationException extends ApiException {
  ValidationException(String detail, dynamic data) 
      : super(message: detail, statusCode: 422, data: data);
}