import 'package:flutter_bloc/flutter_bloc.dart';
import '../../data/repositories/admin_repository.dart';
import 'admin_state.dart';

class AdminCubit extends Cubit<AdminState> {
  final AdminRepository _repository;

  AdminCubit(this._repository) : super(const AdminState());

  Future<void> loadUsers() async {
    emit(state.copyWith(status: AdminStatus.loading));
    try {
      final users = await _repository.listarUsuarios();
      emit(state.copyWith(status: AdminStatus.success, users: users));
    } catch (e) {
      emit(state.copyWith(status: AdminStatus.failure, errorMessage: "Error cargando usuarios: $e"));
    }
  }

  Future<void> crearUsuario({
    required String username, 
    required String email, 
    required String password, 
    required String rol,
    String? nombre,
    String? apellidos,
  }) async {
    emit(state.copyWith(status: AdminStatus.loading));
    try {
      await _repository.crearUsuario(
        username: username, 
        email: email,
        password: password, 
        rol: rol,
        nombre: nombre,
        apellidos: apellidos
      );
      emit(state.copyWith(successMessage: "Usuario creado correctamente"));
      loadUsers();
    } catch (e) {
      emit(state.copyWith(status: AdminStatus.failure, errorMessage: "Error creando usuario"));
    }
  }

  Future<void> actualizarUsuario(int id, {
    String? email, 
    String? rol, 
    bool? activo, 
    String? password,
    String? nombre,
    String? apellidos,
  }) async {
    try {
      await _repository.actualizarUsuario(
        id, 
        email: email, 
        rol: rol, 
        activo: activo, 
        password: password,
        nombre: nombre,
        apellidos: apellidos
      );
      emit(state.copyWith(successMessage: "Usuario actualizado"));
      loadUsers();
    } catch (e) {
      emit(state.copyWith(status: AdminStatus.failure, errorMessage: "Error actualizando usuario"));
    }
  }

  Future<void> eliminarUsuario(int id) async {
    try {
      await _repository.eliminarUsuario(id);
      emit(state.copyWith(successMessage: "Usuario eliminado"));
      loadUsers();
    } catch (e) {
      emit(state.copyWith(status: AdminStatus.failure, errorMessage: "Error eliminando usuario"));
    }
  }
}