import 'dart:io';
import 'package:flutter/material.dart';
import 'package:pdfrx/pdfrx.dart'; // <--- LIBRERÍA COMPATIBLE WINDOWS/MOVIL
import 'package:photo_view/photo_view.dart';

class UniversalFileViewer extends StatelessWidget {
  final String filePath;
  final String fileName;

  const UniversalFileViewer({
    super.key, 
    required this.filePath, 
    required this.fileName
  });

  @override
  Widget build(BuildContext context) {
    final extension = fileName.split('.').last.toLowerCase();
    Widget content;

    if (['jpg', 'jpeg', 'png', 'webp'].contains(extension)) {
      content = PhotoView(
        imageProvider: FileImage(File(filePath)),
        minScale: PhotoViewComputedScale.contained,
        backgroundDecoration: const BoxDecoration(color: Colors.black),
      );
    } else if (extension == 'pdf') {
      // PdfViewer de pdfrx funciona nativamente en Windows y Móvil
      content = PdfViewer.file(
        filePath,
        params: PdfViewerParams(
          backgroundColor: Colors.black,
          loadingBannerBuilder: (context, bytesDownloaded, totalBytes) {
            return const Center(
              child: CircularProgressIndicator(color: Colors.white),
            );
          },
          errorBannerBuilder: (context, error, stackTrace, documentRef) {
             return Center(
               child: Text("Error al cargar PDF: $error", 
               style: const TextStyle(color: Colors.white))
             );
          },
        ),
      );
    } else {
      // Texto plano o fallback
      content = FutureBuilder<String>(
        future: File(filePath).readAsString(),
        builder: (context, snapshot) {
          if (snapshot.hasData) {
            return SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Text(
                snapshot.data!, 
                style: const TextStyle(color: Colors.white, fontFamily: 'Courier'),
              ),
            );
          } else if (snapshot.hasError) {
             return const Center(
               child: Text("No se puede previsualizar este archivo.", 
               style: TextStyle(color: Colors.white70))
             );
          }
          return const Center(child: CircularProgressIndicator());
        },
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(fileName),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        actions: [
          // Opción para abrir con la app del sistema por si acaso
          IconButton(
            icon: const Icon(Icons.open_in_new),
            tooltip: "Abrir externo",
            onPressed: () {
              // Aquí usaremos open_filex más adelante si quieres
            },
          )
        ],
      ),
      backgroundColor: Colors.black,
      body: SafeArea(child: content),
    );
  }
}