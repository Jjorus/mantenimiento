import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/admin_cubit/admin_cubit.dart';
import '../../../../data/models/user_model.dart';

class UserFormDialog extends StatefulWidget {
  final UserModel? user;
  const UserFormDialog({super.key, this.user});

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
    _ubiCtrl = TextEditingController(
      text: widget.user?.ubicacionId?.toString() ?? "",
    );
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

  void _submit() {
    if (_formKey.currentState!.validate()) {
      final ubiText = _ubiCtrl.text.trim();
      final int? ubicacionId =
          ubiText.isEmpty ? null : int.tryParse(ubiText);

      if (widget.user == null) {
        // Crear
        context.read<AdminCubit>().crearUsuario(
              username: _userCtrl.text,
              email: _emailCtrl.text,
              password: _passCtrl.text,
              rol: _rol,
              nombre: _nomCtrl.text,
              apellidos: _apeCtrl.text,
              ubicacionId: ubicacionId,
            );
      } else {
        // Editar
        context.read<AdminCubit>().actualizarUsuario(
              widget.user!.id,
              email: _emailCtrl.text,
              rol: _rol,
              activo: _activo,
              password:
                  _passCtrl.text.isNotEmpty ? _passCtrl.text : null,
              nombre: _nomCtrl.text,
              apellidos: _apeCtrl.text,
              ubicacionId: ubicacionId,
            );
      }
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.user != null;
    return AlertDialog(
      title: Text(isEditing ? "Editar Usuario" : "Nuevo Usuario"),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _userCtrl,
                  decoration:
                      const InputDecoration(labelText: "Username"),
                  validator: (v) =>
                      v!.isEmpty ? "Requerido" : null,
                  enabled: !isEditing,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _emailCtrl,
                  decoration:
                      const InputDecoration(labelText: "Email"),
                  validator: (v) => v!.isEmpty || !v.contains('@')
                      ? "Email inválido"
                      : null,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _ubiCtrl,
                  decoration: const InputDecoration(
                    labelText: "Ubicación (ID Técnico)",
                    helperText:
                        "Opcional. Debe existir una ubicación de tipo TÉCNICO",
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 10),
                // FILA DE NOMBRE Y APELLIDOS
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _nomCtrl,
                        decoration: const InputDecoration(
                          labelText: "Nombre",
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextFormField(
                        controller: _apeCtrl,
                        decoration: const InputDecoration(
                          labelText: "Apellidos",
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _passCtrl,
                  decoration: InputDecoration(
                    labelText: isEditing
                        ? "Nueva Contraseña (vacío para mantener)"
                        : "Contraseña",
                  ),
                  obscureText: true,
                  validator: (v) => (!isEditing && v!.isEmpty)
                      ? "Requerido"
                      : null,
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: _rol,
                  decoration:
                      const InputDecoration(labelText: "Rol"),
                  items: ["ADMIN", "MANTENIMIENTO", "OPERARIO"]
                      .map(
                        (r) => DropdownMenuItem(
                          value: r,
                          child: Text(r),
                        ),
                      )
                      .toList(),
                  onChanged: (v) =>
                      setState(() => _rol = v ?? "OPERARIO"),
                ),
                if (isEditing)
                  SwitchListTile(
                    title: const Text("Usuario Activo"),
                    value: _activo,
                    onChanged: (v) =>
                        setState(() => _activo = v),
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
        if (isEditing)
          TextButton(
            onPressed: () {
              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text("Eliminar"),
                  content: const Text("¿Seguro?"),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text("No"),
                    ),
                    TextButton(
                      onPressed: () {
                        context
                            .read<AdminCubit>()
                            .eliminarUsuario(widget.user!.id);
                        Navigator.pop(ctx);
                        Navigator.pop(context);
                      },
                      child: const Text(
                        "Sí, Eliminar",
                        style: TextStyle(color: Colors.red),
                      ),
                    ),
                  ],
                ),
              );
            },
            child: const Text(
              "Eliminar",
              style: TextStyle(color: Colors.red),
            ),
          ),
        ElevatedButton(
          onPressed: _submit,
          child: const Text("Guardar"),
        ),
      ],
    );
  }
}
