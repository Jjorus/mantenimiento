import 'package:equatable/equatable.dart';
import '../../data/models/user_model.dart';

enum AdminStatus { initial, loading, success, failure }

class AdminState extends Equatable {
  final AdminStatus status;
  final List<UserModel> users;
  final String? errorMessage;
  final String? successMessage;

  const AdminState({
    this.status = AdminStatus.initial,
    this.users = const [],
    this.errorMessage,
    this.successMessage,
  });

  AdminState copyWith({
    AdminStatus? status,
    List<UserModel>? users,
    String? errorMessage,
    String? successMessage,
  }) {
    return AdminState(
      status: status ?? this.status,
      users: users ?? this.users,
      errorMessage: errorMessage, // Si no se pasa, se asume null (resetear error)
      successMessage: successMessage,
    );
  }

  @override
  List<Object?> get props => [status, users, errorMessage, successMessage];
}