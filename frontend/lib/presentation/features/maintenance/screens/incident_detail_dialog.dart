// Ruta: frontend/lib/presentation/features/maintenance/screens/incident_detail_dialog.dart
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/incidencia_model.dart';
import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
import '../../../shared/widgets/files/universal_file_viewer.dart';

class IncidentDetailDialog extends StatefulWidget {
  final IncidenciaModel incidencia;
  const IncidentDetailDialog({super.key, required this.incidencia});

  @override
  State<IncidentDetailDialog> createState() => _IncidentDetailDialogState();
}

class _IncidentDetailDialogState extends State<IncidentDetailDialog> {
  late Future<List<Map<String, String>>> _filesFuture;
  late TextEditingController _descController;
  
  final FocusNode _textFocusNode = FocusNode();
  
  bool _isEditing = false;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _descController = TextEditingController(text: widget.incidencia.descripcion ?? "");
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
      _filesFuture = context.read<MaintenanceRepository>().listarAdjuntosIncidencia(widget.incidencia.id);
    });
  }

  Future<void> _guardarCambios() async {
    setState(() => _isLoading = true);
    try {
      await context.read<MaintenanceCubit>().actualizarIncidencia(
        widget.incidencia.id, 
        descripcion: _descController.text
      );
      if(mounted) {
        setState(() {
          _isEditing = false;
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Incidencia actualizada"), backgroundColor: Colors.green));
      }
    } catch (e) {
      if(mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al actualizar"), backgroundColor: Colors.red));
      }
    }
  }

  Future<void> _uploadFile() async {
    try {
      final result = await FilePicker.platform.pickFiles();
      if (result != null && result.files.single.path != null) {
        final file = File(result.files.single.path!);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Subiendo...")));
        await context.read<MaintenanceCubit>().subirAdjuntoIncidencia(widget.incidencia.id, file);
        if (!mounted) return;
        _refreshFiles();
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Archivo subido con éxito"), backgroundColor: Colors.green));
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al subir"), backgroundColor: Colors.red));
    }
  }

  Future<void> _viewFile(String url, String fileName) async {
    try {
      final file = await context.read<MaintenanceRepository>().descargarArchivo(url, fileName);
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => 
        UniversalFileViewer(filePath: file.path, fileName: fileName)
      ));
    } catch (e) { /* Log */ }
  }

  void _cerrarDialogo() async {
    _textFocusNode.unfocus();
    await Future.delayed(const Duration(milliseconds: 200));
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvoked: (didPop) {
        if(didPop) return;
        _cerrarDialogo();
      },
      child: Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Container(
          width: 800,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              // HEADER
              Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, size: 32, color: Colors.orange),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      "Incidencia #${widget.incidencia.id}: ${widget.incidencia.titulo}",
                      style: Theme.of(context).textTheme.headlineSmall,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(icon: const Icon(Icons.close), onPressed: _cerrarDialogo),
                ],
              ),
              const Divider(),
              
              Expanded(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 5,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("Equipo: ${widget.incidencia.equipoId} | Estado: ${widget.incidencia.estado}", 
                               style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
                          const SizedBox(height: 20),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text("Descripción / Notas", style: Theme.of(context).textTheme.titleMedium),
                              IconButton(
                                onPressed: _isLoading ? null : (_isEditing ? _guardarCambios : () => setState(() => _isEditing = true)),
                                icon: _isLoading
                                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.orange))
                                    : Icon(_isEditing ? Icons.save : Icons.edit, color: Colors.orange),
                              )
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: Container(
                              decoration: BoxDecoration(
                                color: _isEditing ? Colors.white : Colors.grey.withOpacity(0.05),
                                border: Border.all(color: _isEditing ? Colors.orange : Colors.grey.shade300),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: TextField(
                                controller: _descController,
                                focusNode: _textFocusNode, // FOCO ASIGNADO
                                readOnly: !_isEditing || _isLoading,
                                maxLines: null,
                                expands: true,
                                textAlignVertical: TextAlignVertical.top,
                                decoration: const InputDecoration(
                                  border: InputBorder.none,
                                  contentPadding: EdgeInsets.all(12),
                                  hintText: "Descripción del problema...",
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 24),
                    const VerticalDivider(width: 1),
                    const SizedBox(width: 24),
                    Expanded(
                      flex: 3,
                      child: Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text("Adjuntos", style: Theme.of(context).textTheme.titleMedium),
                              ElevatedButton.icon(
                                onPressed: _uploadFile,
                                icon: const Icon(Icons.upload_file, size: 18, color: Colors.orange),
                                label: const Text("Subir", style: TextStyle(color: Colors.orange)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.white,
                                  foregroundColor: Colors.orange,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Expanded(
                            child: Container(
                              decoration: BoxDecoration(
                                border: Border.all(color: Colors.grey.shade300),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: FutureBuilder<List<Map<String, String>>>(
                                future: _filesFuture,
                                builder: (context, snapshot) {
                                  if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
                                  final files = snapshot.data ?? [];
                                  if (files.isEmpty) return const Center(child: Text("Sin adjuntos"));
                                  return ListView.separated(
                                    itemCount: files.length,
                                    separatorBuilder: (_,__) => const Divider(height: 1),
                                    itemBuilder: (ctx, i) {
                                      final f = files[i];
                                      return ListTile(
                                        dense: true,
                                        leading: const Icon(Icons.attach_file, size: 20),
                                        title: Text(f['fileName'] ?? '?', overflow: TextOverflow.ellipsis),
                                        trailing: IconButton(
                                          icon: const Icon(Icons.visibility, color: Colors.orange),
                                          onPressed: () => _viewFile(f['url']!, f['fileName']!),
                                        ),
                                      );
                                    },
                                  );
                                },
                              ),
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
}