// frontend/lib/presentation/features/admin/widgets/user_detail_dialog.dart
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/user_model.dart';
import '../../../../data/repositories/admin_repository.dart';
import '../../../../data/repositories/inventory_repository.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../core/utils/file_downloader.dart';
import '../../../shared/widgets/files/universal_file_viewer.dart';
import 'user_form_dialog.dart';

class UserDetailDialog extends StatefulWidget {
  final UserModel user;

  const UserDetailDialog({super.key, required this.user});

  @override
  State<UserDetailDialog> createState() => _UserDetailDialogState();
}

class _UserDetailDialogState extends State<UserDetailDialog> {
  late Future<List<Map<String, String>>> _filesFuture;
  late TextEditingController _notesController;

  bool _isEditingNotes = false;
  bool _isSavingNotes = false;

  @override
  void initState() {
    super.initState();
    _notesController = TextEditingController(text: widget.user.notas ?? '');
    _refreshFiles();
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  void _refreshFiles() {
    setState(() {
      _filesFuture = context
          .read<AdminRepository>()
          .listarAdjuntosUsuario(widget.user.id);
    });
  }

  Future<void> _guardarNotas() async {
    setState(() {
      _isSavingNotes = true;
    });
    try {
      await context
          .read<AdminRepository>()
          .guardarNotasUsuario(widget.user.id, _notesController.text);

      if (!mounted) return;
      setState(() {
        _isSavingNotes = false;
        _isEditingNotes = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Notas actualizadas'),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isSavingNotes = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error al guardar notas'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _uploadFile() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      withReadStream: true,
    );

    if (result == null || result.files.isEmpty) return;

    final filePath = result.files.single.path;
    if (filePath == null) return;

    final file = File(filePath);

    try {
      await context
          .read<AdminRepository>()
          .subirAdjuntoUsuario(widget.user.id, file);
      _refreshFiles();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Archivo subido correctamente')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error al subir archivo'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _deleteFile(int idAdjunto) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirmar eliminación'),
        content: const Text('¿Estás seguro de eliminar este archivo?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text(
              'Eliminar',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );

    if (confirm != true || !mounted) return;

    try {
      await context
          .read<AdminRepository>()
          .eliminarAdjuntoUsuario(widget.user.id, idAdjunto);
      _refreshFiles();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Archivo eliminado')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error eliminando archivo'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _viewFile(String url, String fileName) async {
    try {
      final file = await context
          .read<InventoryRepository>()
          .descargarArchivo(url, fileName);
      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => UniversalFileViewer(
            filePath: file.path,
            fileName: fileName,
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error al abrir archivo'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _downloadFile(String url, String fileName) async {
    try {
      final repo = context.read<InventoryRepository>();
      final tempFile = await repo.descargarArchivo(url, fileName);
      if (!mounted) return;
      await FileDownloader.saveFile(context, tempFile, fileName);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error al descargar archivo'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _openEditUser() {
    showDialog<void>(
      context: context,
      builder: (_) => UserFormDialog(user: widget.user),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.user;
    final invState = context.watch<InventoryCubit>().state;
    final ubicNombre = user.ubicacionId != null
        ? (invState.ubicaciones[user.ubicacionId!] ?? '-')
        : '-';

    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      child: SizedBox(
        width: 900,
        height: 600,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              // Header
              Row(
                children: [
                  const Icon(
                    Icons.person_outline,
                    size: 32,
                    color: Colors.indigo,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Ficha de usuario: ${user.fullName}',
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          user.email,
                          style: TextStyle(
                            color: Colors.grey.shade700,
                          ),
                        ),
                      ],
                    ),
                  ),
                  TextButton.icon(
                    onPressed: _openEditUser,
                    icon: const Icon(Icons.edit),
                    label: const Text('Editar'),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  )
                ],
              ),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 16),

              // Body: info + notas + adjuntos
              Expanded(
                child: Row(
                  children: [
                    // Columna izquierda: datos del usuario
                    Expanded(
                      flex: 2,
                      child: ListView(
                        children: [
                          _buildInfoRow('ID', user.id.toString()),
                          _buildInfoRow('Usuario', user.username),
                          _buildInfoRow('Nombre', user.nombre ?? '-'),
                          _buildInfoRow('Apellidos', user.apellidos ?? '-'),
                          _buildInfoRow('Rol', user.role),
                          _buildInfoRow(
                              'Activo', user.active ? 'SÍ' : 'NO'),
                          _buildInfoRow('Ubicación', ubicNombre),
                        ],
                      ),
                    ),
                    const VerticalDivider(width: 32),
                    // Columna derecha: notas + adjuntos
                    Expanded(
                      flex: 3,
                      child: Column(
                        children: [
                          // Notas
                          Row(
                            mainAxisAlignment:
                                MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                'Notas internas',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              if (!_isEditingNotes)
                                TextButton.icon(
                                  onPressed: () {
                                    setState(() {
                                      _isEditingNotes = true;
                                    });
                                  },
                                  icon: const Icon(Icons.edit),
                                  label: const Text('Editar notas'),
                                ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: TextField(
                              controller: _notesController,
                              enabled: _isEditingNotes && !_isSavingNotes,
                              maxLines: null,
                              expands: true,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                                hintText: 'Escribe notas internas...',
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (_isEditingNotes)
                            Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                TextButton(
                                  onPressed: _isSavingNotes
                                      ? null
                                      : () {
                                          setState(() {
                                            _isEditingNotes = false;
                                            _notesController.text =
                                                user.notas ?? '';
                                          });
                                        },
                                  child: const Text('Cancelar'),
                                ),
                                const SizedBox(width: 8),
                                ElevatedButton.icon(
                                  onPressed: _isSavingNotes
                                      ? null
                                      : _guardarNotas,
                                  icon: _isSavingNotes
                                      ? const SizedBox(
                                          width: 16,
                                          height: 16,
                                          child:
                                              CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Icon(Icons.save),
                                  label: const Text('Guardar'),
                                ),
                              ],
                            ),
                          const SizedBox(height: 16),
                          const Divider(),
                          const SizedBox(height: 8),

                          // Adjuntos
                          Row(
                            mainAxisAlignment:
                                MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                'Adjuntos',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              TextButton.icon(
                                onPressed: _uploadFile,
                                icon: const Icon(Icons.attach_file),
                                label: const Text('Añadir adjunto'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: FutureBuilder<List<Map<String, String>>>(
                              future: _filesFuture,
                              builder: (context, snapshot) {
                                if (snapshot.connectionState ==
                                    ConnectionState.waiting) {
                                  return const Center(
                                    child: CircularProgressIndicator(),
                                  );
                                }
                                if (snapshot.hasError) {
                                  return const Center(
                                    child:
                                        Text('Error cargando adjuntos'),
                                  );
                                }
                                final files = snapshot.data ?? [];
                                if (files.isEmpty) {
                                  return const Center(
                                    child: Text('Sin adjuntos'),
                                  );
                                }
                                return ListView.builder(
                                  itemCount: files.length,
                                  itemBuilder: (context, index) {
                                    final f = files[index];
                                    final url = f['url']!;
                                    final fileName = f['fileName']!;
                                    final idAdjunto =
                                        int.tryParse(
                                                url.split('/').last) ??
                                            0;

                                    return ListTile(
                                      title: Text(fileName),
                                      trailing: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          IconButton(
                                            icon: const Icon(
                                              Icons.visibility,
                                              color: Colors.blue,
                                            ),
                                            tooltip: 'Ver',
                                            onPressed: () =>
                                                _viewFile(
                                                    url, fileName),
                                          ),
                                          IconButton(
                                            icon: const Icon(
                                              Icons.download,
                                              color: Colors.green,
                                            ),
                                            tooltip:
                                                'Guardar como...',
                                            onPressed: () =>
                                                _downloadFile(
                                                    url, fileName),
                                          ),
                                          IconButton(
                                            icon: const Icon(
                                              Icons.delete,
                                              color: Colors.red,
                                            ),
                                            tooltip: 'Eliminar',
                                            onPressed: () =>
                                                _deleteFile(
                                                    idAdjunto),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.grey.shade700,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(value),
          ),
        ],
      ),
    );
  }
}
