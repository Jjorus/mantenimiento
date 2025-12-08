// Ruta: frontend/lib/presentation/features/maintenance/screens/repair_detail_dialog.dart
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/reparacion_model.dart';
import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../core/api/api_exception.dart';
import '../../../../core/utils/file_downloader.dart';
import '../../../shared/widgets/files/universal_file_viewer.dart';

class RepairDetailDialog extends StatefulWidget {
  final ReparacionModel reparacion;

  const RepairDetailDialog({
    super.key,
    required this.reparacion,
  });

  @override
  State<RepairDetailDialog> createState() => _RepairDetailDialogState();
}

class _RepairDetailDialogState extends State<RepairDetailDialog> {
  late Future<List<Map<String, dynamic>>> _filesFuture;
  late TextEditingController _descController;
  final FocusNode _textFocusNode = FocusNode();

  bool _isEditing = false;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _descController =
        TextEditingController(text: widget.reparacion.descripcion ?? "");
    _refreshFiles();
  }

  @override
  void dispose() {
    _descController.dispose();
    _textFocusNode.dispose();
    super.dispose();
  }

  void _refreshFiles() {
    setState(() {
      _filesFuture = context
          .read<MaintenanceRepository>()
          .listarFacturas(widget.reparacion.id);
    });
  }

  String _formatDateTime(String? iso) {
    if (iso == null || iso.isEmpty) return "-";
    try {
      final dt = DateTime.parse(iso).toLocal();
      return "${dt.day.toString().padLeft(2, '0')}/"
          "${dt.month.toString().padLeft(2, '0')}/"
          "${dt.year} "
          "${dt.hour.toString().padLeft(2, '0')}:"
          "${dt.minute.toString().padLeft(2, '0')}";
    } catch (_) {
      return iso;
    }
  }

  Color _estadoColor(String estado) {
    switch (estado) {
      case 'ABIERTA':
        return Colors.orange;
      case 'EN_PROGRESO':
        return Colors.blue;
      case 'CERRADA':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  Future<void> _guardarDescripcion() async {
    setState(() {
      _isSaving = true;
    });
    try {
      // Aquí de momento no tocamos backend (mantengo el comportamiento
      // que ya tenías). Solo cerramos edición y mostramos aviso local.
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content:
              Text("Descripción actualizada (no enviada todavía al servidor)"),
        ),
      );
      setState(() {
        _isEditing = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message),
          backgroundColor: Colors.red,
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Error al guardar descripción"),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _subirAdjunto() async {
    try {
      final result = await FilePicker.platform.pickFiles();
      if (result == null || result.files.single.path == null) return;

      final file = File(result.files.single.path!);
      final repo = context.read<MaintenanceRepository>();

      await repo.subirFactura(widget.reparacion.id, file);

      if (!mounted) return;
      _refreshFiles();

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Adjunto subido correctamente"),
          backgroundColor: Colors.green,
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Error subiendo adjunto"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _eliminarAdjunto(int adjuntoId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Eliminar adjunto"),
        content: const Text(
            "¿Seguro que deseas eliminar este adjunto? Esta acción no se puede deshacer."),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text("Cancelar"),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text(
              "Eliminar",
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      final repo = context.read<MaintenanceRepository>();
      await repo.eliminarFactura(widget.reparacion.id, adjuntoId);

      if (!mounted) return;
      _refreshFiles();

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Adjunto eliminado"),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Error eliminando adjunto"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _verAdjunto(String url, String fileName) async {
    try {
      final repo = context.read<MaintenanceRepository>();
      final file = await repo.descargarArchivo(url, fileName);
      if (!mounted) return;

      Navigator.of(context).push(
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
          content: Text("Error al abrir adjunto"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _guardarAdjuntoComo(String url, String fileName) async {
    try {
      final repo = context.read<MaintenanceRepository>();
      final file = await repo.descargarArchivo(url, fileName);
      if (!mounted) return;

      await FileDownloader.saveFile(context, file, fileName);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Error al guardar adjunto"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final rep = widget.reparacion;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SizedBox(
        width: 900,
        height: 600,
        child: Column(
          children: [
            // HEADER
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Row(
                children: [
                  const Icon(Icons.build, color: Colors.indigo),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Reparación #${rep.id} · Equipo ${rep.equipoId}",
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        Text(
                          rep.titulo,
                          style: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(color: Colors.grey[700]),
                        ),
                        if (rep.incidenciaId != null)
                          Text(
                            "Incidencia asociada: #${rep.incidenciaId}",
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: Colors.grey[600]),
                          ),
                      ],
                    ),
                  ),
                  Chip(
                    label: Text(
                      rep.estado,
                      style: const TextStyle(color: Colors.white),
                    ),
                    backgroundColor: _estadoColor(rep.estado),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                child: Row(
                  children: [
                    // IZQUIERDA: DESCRIPCIÓN
                    Expanded(
                      flex: 2,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "Descripción de la reparación",
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: _isEditing
                                      ? Colors.indigo
                                      : Colors.grey.shade300,
                                ),
                                color: _isEditing
                                    ? Colors.white
                                    : Colors.grey.shade50,
                              ),
                              child: TextField(
                                focusNode: _textFocusNode,
                                controller: _descController,
                                readOnly: !_isEditing,
                                maxLines: null,
                                expands: true,
                                textAlignVertical: TextAlignVertical.top,
                                decoration: const InputDecoration(
                                  border: InputBorder.none,
                                  contentPadding: EdgeInsets.all(12),
                                  hintText:
                                      "Añade detalles de la reparación, trabajos realizados, piezas, etc.",
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              TextButton.icon(
                                icon: Icon(
                                  _isEditing
                                      ? Icons.cancel_outlined
                                      : Icons.edit_outlined,
                                ),
                                label: Text(
                                  _isEditing
                                      ? "Cancelar edición"
                                      : "Editar",
                                ),
                                onPressed: () {
                                  setState(() {
                                    if (_isEditing) {
                                      _descController.text =
                                          widget.reparacion
                                                  .descripcion ??
                                              "";
                                    }
                                    _isEditing = !_isEditing;
                                  });
                                  if (_isEditing) {
                                    _textFocusNode.requestFocus();
                                  }
                                },
                              ),
                              const SizedBox(width: 8),
                              if (_isEditing)
                                ElevatedButton.icon(
                                  icon: _isSaving
                                      ? const SizedBox(
                                          width: 14,
                                          height: 14,
                                          child:
                                              CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Icon(Icons.save),
                                  label: const Text("Guardar"),
                                  onPressed:
                                      _isSaving ? null : _guardarDescripcion,
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 24),
                    // DERECHA: ADJUNTOS
                    Expanded(
                      flex: 2,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Text(
                                "Adjuntos",
                                style: Theme.of(context)
                                    .textTheme
                                    .titleSmall
                                    ?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                              ),
                              const Spacer(),
                              IconButton(
                                icon: const Icon(Icons.add),
                                tooltip: "Subir adjunto",
                                onPressed: _subirAdjunto,
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: FutureBuilder<
                                List<Map<String, dynamic>>>(
                              future: _filesFuture,
                              builder: (context, snapshot) {
                                if (snapshot.connectionState ==
                                    ConnectionState.waiting) {
                                  return const Center(
                                    child:
                                        CircularProgressIndicator(),
                                  );
                                }
                                if (snapshot.hasError) {
                                  return const Center(
                                    child: Text(
                                        "Error cargando adjuntos"),
                                  );
                                }
                                final files = snapshot.data ?? [];
                                if (files.isEmpty) {
                                  return const Center(
                                    child: Text("Sin adjuntos"),
                                  );
                                }
                                return ListView.builder(
                                  itemCount: files.length,
                                  itemBuilder: (context, index) {
                                    final f = files[index];
                                    final idAdjunto =
                                        f['id'] as int? ?? 0;
                                    final nombre =
                                        (f['nombre_archivo'] ??
                                                'adjunto')
                                            .toString();
                                    final esPrincipal =
                                        (f['es_principal'] as bool?) ??
                                            false;
                                    final fechaSubida =
                                        f['fecha_subida'] as String?;
                                    final url =
                                        '/v1/reparaciones/${widget.reparacion.id}/facturas/$idAdjunto';

                                    return ListTile(
                                      leading: Icon(
                                        esPrincipal
                                            ? Icons.star
                                            : Icons
                                                .description_outlined,
                                        color: esPrincipal
                                            ? Colors.amber
                                            : Colors.blueGrey,
                                      ),
                                      title: Text(nombre),
                                      subtitle: fechaSubida != null
                                          ? Text(
                                              "Subido: ${_formatDateTime(fechaSubida)}",
                                              style:
                                                  const TextStyle(
                                                fontSize: 11,
                                                color:
                                                    Colors.grey,
                                              ),
                                            )
                                          : null,
                                      trailing: Row(
                                        mainAxisSize:
                                            MainAxisSize.min,
                                        children: [
                                          IconButton(
                                            icon: const Icon(
                                              Icons
                                                  .visibility_outlined,
                                              color: Colors.blue,
                                            ),
                                            tooltip: "Ver",
                                            onPressed: () =>
                                                _verAdjunto(
                                              url,
                                              nombre,
                                            ),
                                          ),
                                          IconButton(
                                            icon: const Icon(
                                              Icons.download,
                                              color: Colors.green,
                                            ),
                                            tooltip: "Guardar como...",
                                            onPressed: () =>
                                                _guardarAdjuntoComo(
                                              url,
                                              nombre,
                                            ),
                                          ),
                                          IconButton(
                                            icon: const Icon(
                                              Icons.delete,
                                              color: Colors.red,
                                            ),
                                            tooltip: "Eliminar",
                                            onPressed: () =>
                                                _eliminarAdjunto(
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
            ),
          ],
        ),
      ),
    );
  }
}
