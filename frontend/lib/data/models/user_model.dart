import 'package:json_annotation/json_annotation.dart';

part 'user_model.g.dart';

@JsonSerializable()
class UserModel {
  final int id;
  final String username;
  final String email;
  final String role; // 'ADMIN', 'MANTENIMIENTO', 'OPERARIO'
  final bool active;
  
  // --- NUEVOS CAMPOS ---
  final String? nombre;
  final String? apellidos;

  const UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.active,
    this.nombre,
    this.apellidos,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => _$UserModelFromJson(json);
  Map<String, dynamic> toJson() => _$UserModelToJson(this);

  bool get isAdmin => role == 'ADMIN';
  bool get isMaintenance => role == 'MANTENIMIENTO';
  bool get isTechnician => role == 'OPERARIO';
  
  // Helper útil para mostrar el nombre completo en la UI
  String get fullName {
    final n = nombre ?? '';
    final a = apellidos ?? '';
    if (n.isEmpty && a.isEmpty) return username;
    return "$n $a".trim();
  }
}