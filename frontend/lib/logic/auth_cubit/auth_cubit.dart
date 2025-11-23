import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:dio/dio.dart'; // Necesario para capturar DioException

import '../../data/repositories/auth_repository.dart';
import '../../core/api/api_exception.dart';
import 'auth_state.dart';

class AuthCubit extends Cubit<AuthState> {
  final AuthRepository _authRepository;

  AuthCubit(this._authRepository) : super(const AuthState.unknown()) {
    _checkAuthStatus();
  }

  /// Verifica sesión al arrancar la app
  Future<void> _checkAuthStatus() async {
    try {
      // Pequeño delay para evitar "flickeo" en pantallas rápidas
      await Future.delayed(const Duration(milliseconds: 500));
      
      final user = await _authRepository.checkAuthStatus();
      
      if (user != null) {
        emit(AuthState.authenticated(user));
      } else {
        emit(const AuthState.unauthenticated());
      }
    } catch (_) {
      // Si falla el storage o algo grave, asumimos logout
      emit(const AuthState.unauthenticated());
    }
  }

  /// Login
  Future<void> login(String username, String password) async {
    try {
      final user = await _authRepository.login(username, password);
      emit(AuthState.authenticated(user));
      
    } on DioException catch (e) {
      // CORRECCIÓN: Extraemos el error interno que nuestro interceptor personalizó
      final err = e.error;

      if (err is ApiException) {
        // Error de dominio (401, 422, 403...) -> Mensaje limpio
        emit(AuthState.unauthenticated(error: err.message));
      } else {
        // Error de red puro (sin respuesta del servidor)
        emit(const AuthState.unauthenticated(
          error: "Error de conexión. Verifica tu red.",
        ));
      }
      
    } catch (e) {
      // Error de programación o inesperado
      emit(const AuthState.unauthenticated(
        error: "Error inesperado. Inténtalo de nuevo.",
      ));
    }
  }

  /// Logout
  Future<void> logout() async {
    await _authRepository.logout();
    emit(const AuthState.unauthenticated());
  }
}