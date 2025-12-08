// Ruta: frontend/lib/presentation/features/maintenance/screens/repair_detail_dialog.dart
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/reparacion_model.dart';
import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
import '../../../../core/api/api_exception.dart';
import '../../../../core/utils/file_downloader.dart';
import '../../../shared/widgets/files/universal_file_viewer.dart';
import '../widgets/repair_costs_widget.dart'; // <--- Widget que gestiona los costes

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
  // Variables para Adjuntos
  late Future<List<Map<String, dynamic>>> _filesFuture;
  
  // Variables para Descripción
  late TextEditingController _descController;
  final FocusNode _textFocusNode = FocusNode();
  bool _isEditing = false;
  bool _isSaving = false;

  // NOTA: He eliminado las variables de costes (_gastosFuture, controllers, etc.)
  // porque ahora esa lógica vive dentro de RepairCostsWidget.

  @override
  void initState() {
    super.initState();
    _descController = TextEditingController(text: widget.reparacion.descripcion ?? "");
    _refreshFiles();
  }

  @override
  void dispose() {
    _descController.dispose();
    _textFocusNode.dispose();
    super.dispose();
  }

  // --- MÉTODOS DE DATOS ---

  void _refreshFiles() {
    setState(() {
      _filesFuture = context
          .read<MaintenanceRepository>()
          .listarFacturas(widget.reparacion.id);
    });
  }

  // --- DESCRIPCIÓN ---

  Future<void> _guardarDescripcion() async {
    FocusScope.of(context).unfocus();
    setState(() => _isSaving = true);
    try {
      await context.read<MaintenanceCubit>().actualizarReparacion(
            widget.reparacion.id,
            descripcion: _descController.text,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Descripción actualizada"), backgroundColor: Colors.green));
      setState(() => _isEditing = false);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message), backgroundColor: Colors.red));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al guardar"), backgroundColor: Colors.red));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  void _abrirEditorPantallaCompleta() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => Scaffold(
          appBar: AppBar(
            title: const Text("Editar Descripción (Pantalla Completa)"),
            actions: [IconButton(icon: const Icon(Icons.check), onPressed: () => Navigator.pop(context))],
          ),
          body: Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _descController,
              maxLines: null,
              expands: true,
              autofocus: true,
              style: const TextStyle(fontSize: 16),
              decoration: const InputDecoration(border: InputBorder.none, hintText: "Escribe aquí..."),
            ),
          ),
        ),
      ),
    ).then((_) {
      if (_descController.text != (widget.reparacion.descripcion ?? "")) {
        setState(() => _isEditing = true);
      }
    });
  }

  // --- ADJUNTOS ---

  Future<void> _subirAdjunto() async {
    try {
      final result = await FilePicker.platform.pickFiles();
      if (result == null || result.files.single.path == null) return;
      final file = File(result.files.single.path!);
      await context.read<MaintenanceRepository>().subirFactura(widget.reparacion.id, file);
      if (!mounted) return;
      _refreshFiles();
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Adjunto subido"), backgroundColor: Colors.green));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error subiendo adjunto"), backgroundColor: Colors.red));
    }
  }

  Future<void> _eliminarAdjunto(int adjuntoId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Eliminar adjunto"),
        content: const Text("¿Seguro que deseas eliminar este archivo?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancelar")),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Eliminar", style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await context.read<MaintenanceRepository>().eliminarFactura(widget.reparacion.id, adjuntoId);
      if (!mounted) return;
      _refreshFiles();
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Adjunto eliminado")));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error eliminando adjunto"), backgroundColor: Colors.red));
    }
  }

  // Helpers de adjuntos (ver, descargar)
  Future<void> _verAdjunto(String url, String fileName) async {
     try {
      final file = await context.read<MaintenanceRepository>().descargarArchivo(url, fileName);
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => UniversalFileViewer(filePath: file.path, fileName: fileName)));
    } catch (_) {
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al abrir"), backgroundColor: Colors.red));
    }
  }
  Future<void> _guardarAdjuntoComo(String url, String fileName) async {
     try {
      final file = await context.read<MaintenanceRepository>().descargarArchivo(url, fileName);
      if (!mounted) return;
      await FileDownloader.saveFile(context, file, fileName);
    } catch (_) {
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al guardar"), backgroundColor: Colors.red));
    }
  }

  // --- UI HELPERS ---
  
  String _formatDateTime(String? iso) {
    if (iso == null || iso.isEmpty) return "-";
    try {
      final dt = DateTime.parse(iso).toLocal();
      return "${dt.day}/${dt.month}/${dt.year} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}";
    } catch (_) { return iso; }
  }

  Color _estadoColor(String estado) {
    switch (estado) {
      case 'ABIERTA': return Colors.orange;
      case 'EN_PROGRESO': return Colors.blue;
      case 'CERRADA': return Colors.green;
      default: return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final rep = widget.reparacion;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SizedBox(
        width: 950, 
        height: 650,
        child: Column(
          children: [
            // HEADER
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                children: [
                  const Icon(Icons.build_circle_outlined, color: Colors.indigo, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Reparación #${rep.id} · Equipo ${rep.equipoId}", style: Theme.of(context).textTheme.titleLarge),
                        Text(rep.titulo, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[700])),
                        if (rep.incidenciaId != null)
                          Text("Incidencia origen: #${rep.incidenciaId}", style: const TextStyle(fontSize: 12, color: Colors.grey)),
                      ],
                    ),
                  ),
                  Chip(
                    label: Text(rep.estado, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)), 
                    backgroundColor: _estadoColor(rep.estado)
                  ),
                  const SizedBox(width: 8),
                  IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
                ],
              ),
            ),
            const Divider(height: 1),
            
            // BODY
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // --- COLUMNA IZQUIERDA: DESCRIPCIÓN ---
                    Expanded(
                      flex: 5,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text("Informe técnico", style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
                              IconButton(
                                icon: const Icon(Icons.fullscreen),
                                tooltip: "Pantalla completa",
                                onPressed: () {
                                  setState(() => _isEditing = true);
                                  _abrirEditorPantallaCompleta();
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: _isEditing ? Colors.indigo : Colors.grey.shade300),
                                color: _isEditing ? Colors.white : Colors.grey.shade50,
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
                                  contentPadding: EdgeInsets.all(16),
                                  hintText: "Detalla aquí el trabajo realizado, diagnóstico, etc...",
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              OutlinedButton.icon(
                                icon: Icon(_isEditing ? Icons.cancel : Icons.edit),
                                label: Text(_isEditing ? "Cancelar" : "Editar"),
                                onPressed: () {
                                  setState(() {
                                    if (_isEditing) _descController.text = widget.reparacion.descripcion ?? "";
                                    _isEditing = !_isEditing;
                                  });
                                  if (_isEditing) _textFocusNode.requestFocus();
                                },
                              ),
                              const SizedBox(width: 8),
                              if (_isEditing)
                                FilledButton.icon(
                                  icon: _isSaving
                                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                                      : const Icon(Icons.save),
                                  label: const Text("Guardar"),
                                  onPressed: _isSaving ? null : _guardarDescripcion,
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    
                    const SizedBox(width: 24),
                    
                    // --- COLUMNA DERECHA: PESTAÑAS (ADJUNTOS / COSTES) ---
                    Expanded(
                      flex: 4,
                      child: DefaultTabController(
                        length: 2,
                        child: Column(
                          children: [
                            Container(
                              height: 40,
                              decoration: BoxDecoration(
                                color: Colors.grey[200],
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: TabBar(
                                labelColor: Colors.indigo,
                                unselectedLabelColor: Colors.grey[600],
                                indicatorSize: TabBarIndicatorSize.tab,
                                indicator: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(8),
                                  boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4)],
                                ),
                                tabs: const [
                                  Tab(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.attach_file, size: 16), SizedBox(width: 8), Text("Adjuntos")])),
                                  Tab(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.euro, size: 16), SizedBox(width: 8), Text("Costes")])),
                                ],
                              ),
                            ),
                            const SizedBox(height: 12),
                            Expanded(
                              child: TabBarView(
                                children: [
                                  // TAB 1: ADJUNTOS
                                  _buildAdjuntosTab(),
                                  // TAB 2: COSTES
                                  _buildCostesTab(),
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
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAdjuntosTab() {
    return Column(
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            onPressed: _subirAdjunto,
            icon: const Icon(Icons.upload_file),
            label: const Text("Subir archivo"),
          ),
        ),
        const SizedBox(height: 4),
        Expanded(
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: _filesFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
              if (snapshot.hasError) return const Center(child: Text("Error cargando archivos"));
              final files = snapshot.data ?? [];
              if (files.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.folder_open, size: 48, color: Colors.grey[300]),
                      const SizedBox(height: 8),
                      const Text("No hay adjuntos", style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                );
              }
              return ListView.separated(
                itemCount: files.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final f = files[index];
                  final id = f['id'] as int? ?? 0;
                  final nombre = (f['nombre_archivo'] ?? 'adjunto').toString();
                  final esPrincipal = (f['es_principal'] as bool?) ?? false;
                  final url = '/v1/reparaciones/${widget.reparacion.id}/facturas/$id';
                  final fechaSubida = f['fecha_subida'] as String?;

                  return ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                    leading: CircleAvatar(
                      backgroundColor: esPrincipal ? Colors.amber[100] : Colors.blue[50],
                      child: Icon(esPrincipal ? Icons.star : Icons.description, color: esPrincipal ? Colors.orange : Colors.blue, size: 20),
                    ),
                    title: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                    subtitle: fechaSubida != null ? Text("Subido: ${_formatDateTime(fechaSubida)}", style: const TextStyle(fontSize: 11, color: Colors.grey)) : null,
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(icon: const Icon(Icons.visibility, size: 18, color: Colors.blueGrey), onPressed: () => _verAdjunto(url, nombre)),
                        IconButton(icon: const Icon(Icons.download, size: 18, color: Colors.green), onPressed: () => _guardarAdjuntoComo(url, nombre)),
                        IconButton(icon: const Icon(Icons.delete, size: 18, color: Colors.red), onPressed: () => _eliminarAdjunto(id)),
                      ],
                    ),
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildCostesTab() {
    return RepairCostsWidget(reparacionId: widget.reparacion.id);
  }
}