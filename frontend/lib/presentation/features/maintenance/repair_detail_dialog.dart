import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../data/models/reparacion_model.dart';
import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';
// CORRECCIÓN: Import relativo correcto a shared
import '../../../shared/widgets/files/universal_file_viewer.dart';

class RepairDetailDialog extends StatefulWidget {
  final ReparacionModel reparacion;

  const RepairDetailDialog({super.key, required this.reparacion});

  @override
  State<RepairDetailDialog> createState() => _RepairDetailDialogState();
}

class _RepairDetailDialogState extends State<RepairDetailDialog> {
  late Future<List<String>> _filesFuture;

  @override
  void initState() {
    super.initState();
    _refreshFiles();
  }

  void _refreshFiles() {
    setState(() {
      _filesFuture = context
          .read<MaintenanceRepository>()
          .listarFacturas(widget.reparacion.id);
    });
  }

  Future<void> _uploadFile() async {
    try {
      final result = await FilePicker.platform.pickFiles();
      if (result != null && result.files.single.path != null) {
        final file = File(result.files.single.path!);

        // Mostrar indicador de carga simple
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Subiendo archivo...")),
        );

        await context
            .read<MaintenanceCubit>()
            .subirFactura(widget.reparacion.id, file);

        // CORRECCIÓN: Comprobación de mounted antes de setState
        if (!mounted) return;
        
        // Recargamos la lista para ver el nuevo archivo
        _refreshFiles();
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Archivo subido con éxito"), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Error al subir archivo"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _viewFile(String fileUrl) async {
    try {
      final file = await context
          .read<MaintenanceRepository>()
          .descargarArchivo(fileUrl);

      if (!mounted) return;

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => UniversalFileViewer(
            filePath: file.path,
            fileName: fileUrl.split('/').last,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Error al abrir el archivo"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 600, // Ancho cómodo para Windows
        height: 500,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Cabecera
            Row(
              children: [
                const Icon(Icons.build_circle, size: 32, color: Colors.blue),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    "Reparación #${widget.reparacion.id}: ${widget.reparacion.titulo}",
                    style: Theme.of(context).textTheme.headlineSmall,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 16),

            // Detalles
            Text(
              "Estado: ${widget.reparacion.estado}",
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(widget.reparacion.descripcion ?? "Sin descripción detallada"),
            const SizedBox(height: 24),

            // Sección Archivos
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Facturas y Adjuntos",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                ElevatedButton.icon(
                  onPressed: _uploadFile,
                  icon: const Icon(Icons.upload_file),
                  label: const Text("Subir Archivo"),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Lista de Archivos
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: FutureBuilder<List<String>>(
                  future: _filesFuture,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return Center(
                        child: Text("Error al cargar archivos: ${snapshot.error}"),
                      );
                    }
                    final files = snapshot.data ?? [];
                    if (files.isEmpty) {
                      return const Center(
                        child: Text("No hay archivos adjuntos."),
                      );
                    }

                    return ListView.separated(
                      itemCount: files.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final url = files[index];
                        final name = url.split('/').last;
                        return ListTile(
                          leading: const Icon(Icons.attach_file, color: Colors.grey),
                          title: Text(name),
                          trailing: IconButton(
                            icon: const Icon(Icons.visibility, color: Colors.blue),
                            tooltip: "Ver archivo",
                            onPressed: () => _viewFile(url),
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
    );
  }
}