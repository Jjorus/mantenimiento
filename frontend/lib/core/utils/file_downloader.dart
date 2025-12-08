import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

class FileDownloader {
  /// Solicita destino y copia el archivo temporal [sourceFile] a la ruta final.
  static Future<void> saveFile(BuildContext context, File sourceFile, String fileName) async {
    String? savePath;
    
    try {
      if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
        // En escritorio: Diálogo "Guardar como"
        savePath = await FilePicker.platform.saveFile(
          dialogTitle: 'Guardar archivo como...',
          fileName: fileName,
        );
      } else {
        // En Móvil: Guardar en AppDocuments (simulado, lo ideal es share_plus o Android Intent)
        final directory = await getApplicationDocumentsDirectory();
        savePath = "${directory.path}/$fileName";
      }

      if (savePath != null) {
        // Copiar el archivo descargado (que está en cache/temp) a la ruta destino
        await sourceFile.copy(savePath);
        
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Archivo guardado en: $savePath"), backgroundColor: Colors.green),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Error al guardar el archivo"), backgroundColor: Colors.red),
        );
      }
    }
  }
}