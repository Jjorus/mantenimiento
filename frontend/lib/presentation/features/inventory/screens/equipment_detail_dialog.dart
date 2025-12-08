// frontend/lib/presentation/features/inventory/screens/equipment_detail_dialog.dart
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/equipo_model.dart';
import '../../../../data/repositories/inventory_repository.dart';
import '../../../../logic/inventory_cubit/inventory_cubit.dart';
import '../../../../core/utils/file_downloader.dart';
import '../../../shared/widgets/files/universal_file_viewer.dart';
import '../../admin/widgets/equipment_form_dialog.dart';

class EquipmentDetailDialog extends StatefulWidget {
  final EquipoModel equipo;
  final bool isAdminMode; // Nuevo parámetro

  const EquipmentDetailDialog({
    super.key, 
    required this.equipo,
    this.isAdminMode = false, // Por defecto false
  });

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
    _notesController =
        TextEditingController(text: widget.equipo.notas ?? '');
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
          .read<InventoryRepository>()
          .listarAdjuntos(widget.equipo.id);
    });
  }

  Future<void> _guardarNotas() async {
    setState(() {
      _isSavingNotes = true;
    });
    try {
      await context
          .read<InventoryCubit>()
          .guardarNotas(widget.equipo.id, _notesController.text);

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
    try {
      final result = await FilePicker.platform.pickFiles();
      if (result != null && result.files.single.path != null) {
        final file = File(result.files.single.path!);
        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Subiendo...')),
        );

        await context
            .read<InventoryCubit>()
            .subirAdjuntoEquipo(widget.equipo.id, file);

        if (!mounted) return;
        _refreshFiles();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Archivo subido con éxito'),
            backgroundColor: Colors.green,
          ),
        );
      }
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

    if (confirm != true) return;
    if (!mounted) return;

    try {
      await context
          .read<InventoryCubit>()
          .eliminarAdjuntoEquipo(widget.equipo.id, idAdjunto);
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

  /// Botón de "Guardar" → abre diálogo "Guardar como..."
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

  /// Botón de "Ver" → abre visor universal
  Future<void> _viewFile(String url, String fileName) async {
    try {
      final file =
          await context.read<InventoryRepository>().descargarArchivo(
                url,
                fileName,
              );
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

  String _safeStr(String? s) => s ?? '-';

  @override
  Widget build(BuildContext context) {
    // Leemos nombre de ubicación desde InventoryCubit
    final inventoryState = context.watch<InventoryCubit>().state;
    final ubicId = widget.equipo.ubicacionId;
    final ubicacionNombre = ubicId != null
        ? (inventoryState.ubicaciones[ubicId] ?? 'ID $ubicId')
        : '-';

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final valueTextColor = isDark ? Colors.white : Colors.black87;
    final labelColor = isDark ? Colors.grey[300]! : Colors.grey;
    final notesBackgroundColor = _isEditingNotes
        ? (isDark ? Colors.grey[900] : Colors.white)
        : (isDark ? Colors.grey[850] : Colors.grey.shade50);

    Widget infoRow(String label, String val) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            children: [
              SizedBox(
                width: 120,
                child: Text(
                  label,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: labelColor,
                  ),
                ),
              ),
              Expanded(
                child: SelectableText(
                  val,
                  style: TextStyle(
                    fontWeight: FontWeight.w500,
                    color: valueTextColor,
                  ),
                ),
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
            // Header
            Row(
              children: [
                const Icon(
                  Icons.inventory_2,
                  size: 32,
                  color: Colors.indigo,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Ficha de equipo: ${widget.equipo.identidad ?? 'Sin ID'}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                
                // CONDICIONAL PARA EL BOTÓN DE EDITAR
                if (widget.isAdminMode) ...[
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      showDialog(
                        context: context,
                        builder: (_) => BlocProvider.value(
                          value: context.read<InventoryCubit>(),
                          child: EquipmentFormDialog(equipo: widget.equipo),
                        ),
                      ).then((_) {                       
                        if (context.mounted) {
                           context.read<InventoryCubit>().loadInventory();
                        }
                      });
                    },
                    icon: const Icon(Icons.edit),
                    label: const Text('Editar ficha'),
                  ),
                ],

                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const Divider(height: 24),
            Expanded(
              child: Row(
                children: [
                  // Left: Info + notas
                  Expanded(
                    flex: 2,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        infoRow('ID', widget.equipo.id.toString()),
                        infoRow(
                            'Identidad', _safeStr(widget.equipo.identidad)),
                        infoRow('N. Serie',
                            _safeStr(widget.equipo.numeroSerie)),
                        infoRow('Tipo', widget.equipo.tipo),
                        infoRow('Estado', widget.equipo.estado),
                        infoRow('NFC', _safeStr(widget.equipo.nfcTag)),
                        infoRow('Ubicación', ubicacionNombre),
                        infoRow(
                          'Sección',
                          widget.equipo.seccionId?.toString() ?? '-',
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Notas',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Expanded(
                          child: Container(
                            decoration: BoxDecoration(
                              border: Border.all(
                                color: _isEditingNotes
                                    ? Colors.indigo
                                    : Colors.grey.shade300,
                              ),
                              borderRadius: BorderRadius.circular(8),
                              color: notesBackgroundColor,
                            ),
                            child: TextField(
                              controller: _notesController,
                              readOnly: !_isEditingNotes,
                              maxLines: null,
                              expands: true,
                              textAlignVertical: TextAlignVertical.top,
                              style: TextStyle(
                                color:
                                    isDark ? Colors.white : Colors.black87,
                              ),
                              decoration: const InputDecoration(
                                border: InputBorder.none,
                                contentPadding: EdgeInsets.all(12),
                                hintText: 'Añadir comentarios...',
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            TextButton(
                              onPressed: () {
                                setState(() {
                                  _isEditingNotes = !_isEditingNotes;
                                });
                              },
                              child: Text(
                                _isEditingNotes ? 'Cancelar' : 'Editar notas',
                              ),
                            ),
                            const SizedBox(width: 8),
                            if (_isEditingNotes)
                              ElevatedButton(
                                onPressed:
                                    _isSavingNotes ? null : _guardarNotas,
                                child: _isSavingNotes
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                        ),
                                      )
                                    : const Text('Guardar notas'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 24),
                  // Right: Adjuntos
                  Expanded(
                    flex: 2,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            const Text(
                              'Adjuntos',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.grey,
                              ),
                            ),
                            const Spacer(),
                            IconButton(
                              icon: const Icon(Icons.add),
                              tooltip: 'Subir archivo',
                              onPressed: _uploadFile,
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
                                  child: Text('Error cargando adjuntos'),
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
                                      int.tryParse(url.split('/').last) ??
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
                                              _viewFile(url, fileName),
                                        ),
                                        IconButton(
                                          icon: const Icon(
                                            Icons.download,
                                            color: Colors.green,
                                          ),
                                          tooltip: 'Guardar como...',
                                          onPressed: () =>
                                              _downloadFile(url, fileName),
                                        ),
                                        IconButton(
                                          icon: const Icon(
                                            Icons.delete,
                                            color: Colors.red,
                                          ),
                                          tooltip: 'Eliminar',
                                          onPressed: () =>
                                              _deleteFile(idAdjunto),
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
    );
  }
}