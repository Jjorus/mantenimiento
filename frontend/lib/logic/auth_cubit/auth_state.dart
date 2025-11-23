import 'package:equatable/equatable.dart';
import '../../data/models/user_model.dart';

enum AuthStatus { 
  unknown,          // Arrancando / Splash Screen
  authenticated,    // Sesión activa
  unauthenticated   // Login necesario o fallido
}

class AuthState extends Equatable {
  final AuthStatus status;
  final UserModel? user;
  final String? errorMessage;

  const AuthState._({
    this.status = AuthStatus.unknown,
    this.user,
    this.errorMessage,
  });

  // Estado Inicial (Splash)
  const AuthState.unknown() : this._();

  // Estado Login / Error
  const AuthState.unauthenticated({String? error}) 
      : this._(status: AuthStatus.unauthenticated, errorMessage: error);

  // Estado Sesión Activa
  const AuthState.authenticated(UserModel user) 
      : this._(status: AuthStatus.authenticated, user: user);

  @override
  List<Object?> get props => [status, user, errorMessage];
}