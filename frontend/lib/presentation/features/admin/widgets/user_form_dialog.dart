// Ruta: frontend/lib/presentation/features/admin/widgets/user_form_dialog.dart

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';

import '../../../../data/models/user_model.dart';
import '../../../../data/repositories/inventory_repository.dart';

class UserFormDialog extends StatefulWidget {
  final UserModel? user;

  const UserFormDialog({
    super.key,
    this.user,
  });

  @override
  State<UserFormDialog> createState() => _UserFormDialogState();
}

class _UserFormDialogState extends State<UserFormDialog> {
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _userCtrl;
  late TextEditingController _emailCtrl;
  late TextEditingController _passCtrl;
  late TextEditingController _nomCtrl;
  late TextEditingController _apeCtrl;
  late TextEditingController _ubiCtrl;

  String _rol = "OPERARIO";
  bool _activo = true;

  @override
  void initState() {
    super.initState();

    _userCtrl = TextEditingController(text: widget.user?.username ?? "");
    _emailCtrl = TextEditingController(text: widget.user?.email ?? "");
    _nomCtrl = TextEditingController(text: widget.user?.nombre ?? "");
    _apeCtrl = TextEditingController(text: widget.user?.apellidos ?? "");
    _passCtrl = TextEditingController();

    // Cada usuario tendrá su propia ubicación particular:
    // este campo es SIEMPRE para crear una ubicación NUEVA.
    _ubiCtrl = TextEditingController();

    _rol = widget.user?.role ?? "OPERARIO";
    _activo = widget.user?.active ?? true;
  }

  @override
  void dispose() {
    _userCtrl.dispose();
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _nomCtrl.dispose();
    _apeCtrl.dispose();
    _ubiCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final username = _userCtrl.text.trim();
    final email = _emailCtrl.text.trim();
    final rawPassword = _passCtrl.text.trim();
    final nombre = _nomCtrl.text.trim().isEmpty ? null : _nomCtrl.text.trim();
    final apellidos =
        _apeCtrl.text.trim().isEmpty ? null : _apeCtrl.text.trim();
    final ubiText = _ubiCtrl.text.trim();

    int? ubicacionId;

    // Cada usuario debe tener su ubicación particular:
    // si se rellena, intentamos CREAR SIEMPRE una nueva ubicación.
    if (ubiText.isNotEmpty) {
      try {
        final inventoryRepo = context.read<InventoryRepository>();
        final nuevaUbic = await inventoryRepo.crearUbicacion(
          nombre: ubiText,
          tipo: 'TECNICO',
        );
        ubicacionId = nuevaUbic.id;
      } catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'No se ha podido crear la ubicación.\n'
              'Es posible que ya exista una ubicación con ese nombre.\n'
              'Cada usuario debe tener una ubicación única, prueba con otro nombre.',
            ),
          ),
        );
        return;
      }
    }

    if (widget.user == null) {
      // Crear → password debe ser SIEMPRE String no nulo
      final String password = rawPassword; // el validador ya obliga a no vacío

      await context.read<AdminCubit>().crearUsuario(
            username: username,
            email: email,
            password: password,
            rol: _rol,
            nombre: nombre,
            apellidos: apellidos,
            ubicacionId: ubicacionId,
          );
    } else {
      // Editar → password solo se manda si el campo NO está vacío
      final String? password =
          rawPassword.isNotEmpty ? rawPassword : null;

      await context.read<AdminCubit>().actualizarUsuario(
            widget.user!.id,
            email: email,
            rol: _rol,
            activo: _activo,
            password: password,
            nombre: nombre,
            apellidos: apellidos,
            ubicacionId: ubicacionId,
          );
    }

    if (!mounted) return;

    // Refrescamos usuarios e inventario para que se actualice todo en la UI
    context.read<AdminCubit>().loadUsers();
    context.read<InventoryCubit>().loadInventory();

    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.user != null;

    return AlertDialog(
      title: Text(isEditing ? "Editar usuario" : "Crear usuario"),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Username
                TextFormField(
                  controller: _userCtrl,
                  decoration: const InputDecoration(
                    labelText: "Usuario",
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return "El usuario es obligatorio";
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 10),

                // Email
                TextFormField(
                  controller: _emailCtrl,
                  decoration: const InputDecoration(
                    labelText: "Email",
                  ),
                  keyboardType: TextInputType.emailAddress,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return "El email es obligatorio";
                    }
                    if (!value.contains('@')) {
                      return "Email no válido";
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 10),

                // Nombre
                TextFormField(
                  controller: _nomCtrl,
                  decoration: const InputDecoration(
                    labelText: "Nombre",
                  ),
                ),
                const SizedBox(height: 10),

                // Apellidos
                TextFormField(
                  controller: _apeCtrl,
                  decoration: const InputDecoration(
                    labelText: "Apellidos",
                  ),
                ),
                const SizedBox(height: 10),

                // Password
                TextFormField(
                  controller: _passCtrl,
                  decoration: InputDecoration(
                    labelText:
                        isEditing ? "Nueva contraseña (opcional)" : "Contraseña",
                    helperText: isEditing
                        ? "Déjalo vacío si no quieres cambiarla"
                        : null,
                  ),
                  obscureText: true,
                  validator: (value) {
                    if (!isEditing) {
                      if (value == null || value.trim().isEmpty) {
                        return "La contraseña es obligatoria";
                      }
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 10),

                // ÚNICAMENTE nueva ubicación particular para el usuario
                TextFormField(
                  controller: _ubiCtrl,
                  decoration: const InputDecoration(
                    labelText: "Nueva ubicación de técnico",
                    helperText: "Cada usuario debe tener su propia ubicación. "
                        "Escribe un nombre único para este usuario.",
                  ),
                  keyboardType: TextInputType.text,
                ),
                const SizedBox(height: 10),

                // Rol
                DropdownButtonFormField<String>(
                  value: _rol,
                  decoration: const InputDecoration(
                    labelText: "Rol",
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: "ADMIN",
                      child: Text("ADMIN"),
                    ),
                    DropdownMenuItem(
                      value: "SUPERVISOR",
                      child: Text("SUPERVISOR"),
                    ),
                    DropdownMenuItem(
                      value: "OPERARIO",
                      child: Text("OPERARIO"),
                    ),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() {
                      _rol = value;
                    });
                  },
                ),
                const SizedBox(height: 10),

                // Activo
                SwitchListTile(
                  title: const Text("Activo"),
                  contentPadding: EdgeInsets.zero,
                  value: _activo,
                  onChanged: (value) {
                    setState(() {
                      _activo = value;
                    });
                  },
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text("Cancelar"),
        ),
        ElevatedButton(
          onPressed: _submit,
          child: const Text("Guardar"),
        ),
      ],
    );
  }
}
