import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/equipo_model.dart';
import '../../../../data/repositories/inventory_repository.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../core/utils/file_downloader.dart';
import '../../../shared/widgets/files/universal_file_viewer.dart';

class EquipmentDetailDialog extends StatefulWidget {
  final EquipoModel equipo;
  const EquipmentDetailDialog({super.key, required this.equipo});

  @override
  State<EquipmentDetailDialog> createState() => _EquipmentDetailDialogState();
}

class _EquipmentDetailDialogState extends State<EquipmentDetailDialog> {
  late Future<List<Map<String, String>>> _filesFuture;
  late TextEditingController _notesController;
  
  bool _isEditingNotes = false;
  bool _isSavingNotes = false;

  @override
  void initState() {
    super.initState();
    _notesController = TextEditingController(text: widget.equipo.notas ?? "");
    _refreshFiles();
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  void _refreshFiles() {
    setState(() {
      _filesFuture = context.read<InventoryRepository>().listarAdjuntos(widget.equipo.id);
    });
  }

  Future<void> _guardarNotas() async {
    setState(() => _isSavingNotes = true);
    try {
      await context.read<InventoryCubit>().guardarNotas(widget.equipo.id, _notesController.text);
      if (mounted) {
        setState(() {
          _isEditingNotes = false;
          _isSavingNotes = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Notas actualizadas")));
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSavingNotes = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al guardar"), backgroundColor: Colors.red));
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
        
        await context.read<InventoryCubit>().subirAdjuntoEquipo(widget.equipo.id, file);
        
        if (!mounted) return;
        _refreshFiles();
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Subido"), backgroundColor: Colors.green));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al subir"), backgroundColor: Colors.red));
    }
  }

  Future<void> _deleteFile(int idAdjunto) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Confirmar eliminación"),
        content: const Text("¿Estás seguro de eliminar este archivo?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancelar")),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Eliminar", style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm == true) {
      if (!mounted) return;
      try {
        await context.read<InventoryCubit>().eliminarAdjuntoEquipo(widget.equipo.id, idAdjunto);
        _refreshFiles();
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Archivo eliminado")));
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al eliminar"), backgroundColor: Colors.red));
      }
    }
  }

  Future<void> _downloadFile(String url, String fileName) async {
     try {
        final repo = context.read<InventoryRepository>();
        final tempFile = await repo.descargarArchivo(url, fileName);
        if(!mounted) return;
        await FileDownloader.saveFile(context, tempFile, fileName);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al descargar"), backgroundColor: Colors.red));
    }
  }

  Future<void> _viewFile(String url, String fileName) async {
    try {
      final file = await context.read<InventoryRepository>().descargarArchivo(url, fileName);
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => UniversalFileViewer(filePath: file.path, fileName: fileName)));
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    // CORRECCIÓN: Añadido color explícito (Colors.black87) para asegurar visibilidad sobre fondo claro
    Widget infoRow(String label, String val) => Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(width: 100, child: Text(label, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.grey))),
          Expanded(
            child: SelectableText(
              val, 
              style: const TextStyle(fontWeight: FontWeight.w500, color: Colors.black87)
            )
          ),
        ],
      ),
    );

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 900,
        height: 600,
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            // HEADER
            Row(
              children: [
                const Icon(Icons.inventory_2, size: 32, color: Colors.indigo),
                const SizedBox(width: 12),
                Text("Ficha de Equipo: ${widget.equipo.identidad ?? 'Sin ID'}", style: Theme.of(context).textTheme.headlineSmall),
                const Spacer(),
                IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
              ],
            ),
            const Divider(height: 30),
            Expanded(
              child: Row(
                children: [
                  // --- COLUMNA IZQUIERDA: DATOS Y NOTAS ---
                  Expanded(
                    flex: 4,
                    child: Column(
                      children: [
                        // Tarjeta Datos Fijos
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(color: Colors.grey.shade50, borderRadius: BorderRadius.circular(8)),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text("Datos Técnicos", style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.black87)),
                              const SizedBox(height: 16),
                              infoRow("ID Interno", "#${widget.equipo.id}"),
                              infoRow("N. Serie", widget.equipo.numeroSerie ?? "-"),
                              infoRow("Tipo", widget.equipo.tipo),
                              infoRow("Estado", widget.equipo.estado),
                              infoRow("Ubicación ID", widget.equipo.ubicacionId?.toString() ?? "Sin ubicación"),
                              infoRow("NFC Tag", widget.equipo.nfcTag ?? "-"),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        // Sección Notas
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text("Notas / Comentarios", style: Theme.of(context).textTheme.titleMedium),
                                  IconButton(
                                    onPressed: _isSavingNotes ? null : (_isEditingNotes ? _guardarNotas : () => setState(() => _isEditingNotes = true)),
                                    icon: _isSavingNotes 
                                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                      : Icon(_isEditingNotes ? Icons.save : Icons.edit, color: Colors.indigo),
                                  )
                                ],
                              ),
                              const SizedBox(height: 8),
                              Expanded(
                                child: Container(
                                  decoration: BoxDecoration(
                                    border: Border.all(color: _isEditingNotes ? Colors.indigo : Colors.grey.shade300),
                                    borderRadius: BorderRadius.circular(8),
                                    color: _isEditingNotes ? Colors.white : Colors.grey.shade50
                                  ),
                                  child: TextField(
                                    controller: _notesController,
                                    readOnly: !_isEditingNotes,
                                    maxLines: null,
                                    expands: true,
                                    textAlignVertical: TextAlignVertical.top,
                                    style: const TextStyle(color: Colors.black87), // Asegurar color en input
                                    decoration: const InputDecoration(
                                      border: InputBorder.none,
                                      contentPadding: EdgeInsets.all(12),
                                      hintText: "Añadir comentarios...",
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 24),
                  // --- COLUMNA DERECHA: ADJUNTOS ---
                  Expanded(
                    flex: 6,
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text("Adjuntos", style: Theme.of(context).textTheme.titleMedium),
                            ElevatedButton.icon(
                              onPressed: _uploadFile,
                              icon: const Icon(Icons.upload_file, size: 18),
                              label: const Text("Añadir"),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Expanded(
                          child: Container(
                            decoration: BoxDecoration(border: Border.all(color: Colors.grey.shade300), borderRadius: BorderRadius.circular(8)),
                            child: FutureBuilder<List<Map<String, String>>>(
                              future: _filesFuture,
                              builder: (context, snapshot) {
                                if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
                                final files = snapshot.data ?? [];
                                if (files.isEmpty) return const Center(child: Text("No hay archivos adjuntos"));
                                
                                return ListView.separated(
                                  itemCount: files.length,
                                  separatorBuilder: (_,__) => const Divider(height: 1),
                                  itemBuilder: (ctx, i) {
                                    final f = files[i];
                                    final idAdjunto = int.tryParse(f['url']!.split('/').last) ?? 0;

                                    return ListTile(
                                      leading: const Icon(Icons.insert_drive_file, color: Colors.indigo),
                                      title: Text(f['fileName'] ?? 'Archivo'),
                                      trailing: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          IconButton(
                                            icon: const Icon(Icons.visibility, color: Colors.blue),
                                            tooltip: "Ver",
                                            onPressed: () => _viewFile(f['url']!, f['fileName']!),
                                          ),
                                          IconButton(
                                            icon: const Icon(Icons.download, color: Colors.green),
                                            tooltip: "Descargar",
                                            onPressed: () => _downloadFile(f['url']!, f['fileName']!),
                                          ),
                                          IconButton(
                                            icon: const Icon(Icons.delete, color: Colors.red),
                                            tooltip: "Eliminar",
                                            onPressed: () => _deleteFile(idAdjunto),
                                          ),
                                        ],
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
    );
  }
}