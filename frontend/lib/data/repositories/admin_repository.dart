import 'dart:io';

import '../datasources/admin_remote_ds.dart';
import '../models/user_model.dart';

class AdminRepository {
  final AdminRemoteDataSource _remoteDs;

  AdminRepository({required AdminRemoteDataSource remoteDs})
      : _remoteDs = remoteDs;

  Future<List<UserModel>> listarUsuarios() => _remoteDs.getUsers();

  Future<void> crearUsuario({
    required String username,
    required String email,
    required String password,
    required String rol,
    String? nombre,
    String? apellidos,
    int? ubicacionId,
  }) {
    return _remoteDs.createUser({
      'username': username,
      'email': email,
      'password': password,
      'role': rol,
      'active': true,
      'nombre': nombre,
      'apellidos': apellidos,
      if (ubicacionId != null) 'ubicacion_id': ubicacionId,
    });
  }

  Future<void> actualizarUsuario(
    int id, {
    String? email,
    String? rol,
    bool? activo,
    String? password,
    String? nombre,
    String? apellidos,
    int? ubicacionId,
  }) {
    final Map<String, dynamic> data = {};
    if (email != null) data['email'] = email;
    if (rol != null) data['role'] = rol;
    if (activo != null) data['active'] = activo;
    if (password != null && password.isNotEmpty) {
      data['password'] = password;
    }
    if (nombre != null) data['nombre'] = nombre;
    if (apellidos != null) data['apellidos'] = apellidos;
    if (ubicacionId != null) data['ubicacion_id'] = ubicacionId;

    return _remoteDs.updateUser(id, data);
  }

  Future<void> eliminarUsuario(int id) => _remoteDs.deleteUser(id);

    // --- NOTAS Y ADJUNTOS USUARIO ---

  Future<void> guardarNotasUsuario(int id, String notas) =>
      _remoteDs.updateNotasUsuario(id, notas);

  Future<void> subirAdjuntoUsuario(int id, File file) =>
      _remoteDs.uploadAdjuntoUsuario(id, file);

  Future<List<Map<String, String>>> listarAdjuntosUsuario(int id) =>
      _remoteDs.getAdjuntosUsuarioURLs(id);

  Future<void> eliminarAdjuntoUsuario(int userId, int adjuntoId) =>
      _remoteDs.deleteAdjuntoUsuario(userId, adjuntoId);

}
