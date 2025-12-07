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
  String toString() => message;
}

class AuthException extends ApiException {
  AuthException({super.message = "Sesión caducada o credenciales inválidas"})
      : super(statusCode: 401);
}

class PermissionException extends ApiException {
  PermissionException() : super(message: "No tienes permisos para esta acción", statusCode: 403);
}

class ValidationException extends ApiException {
  ValidationException(String detail, dynamic data) 
      : super(message: detail, statusCode: 422, data: data);
}