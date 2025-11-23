import 'package:json_annotation/json_annotation.dart';

part 'user_model.g.dart';

@JsonSerializable()
class UserModel {
  final int id;
  final String username;
  final String email;
  final String role; // 'ADMIN', 'MANTENIMIENTO', 'OPERARIO'
  final bool active;

  const UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.active,
  });

  // Generación automática de JSON
  factory UserModel.fromJson(Map<String, dynamic> json) => _$UserModelFromJson(json);
  Map<String, dynamic> toJson() => _$UserModelToJson(this);

  // Helpers de Roles (muy útiles para la UI)
  bool get isAdmin => role == 'ADMIN';
  bool get isMaintenance => role == 'MANTENIMIENTO';
  bool get isTechnician => role == 'OPERARIO';
}