import 'package:flutter/material.dart';

class DatabaseTab extends StatelessWidget {
  const DatabaseTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.storage, size: 64, color: Colors.grey),
          const SizedBox(height: 16),
          Text("Gestión de Base de Datos", style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          const Text("Funcionalidades futuras: Backups, Importación masiva, Logs de auditoría."),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: null, // Deshabilitado por ahora
            icon: const Icon(Icons.download),
            label: const Text("Exportar Todo (CSV)"),
          )
        ],
      ),
    );
  }
}