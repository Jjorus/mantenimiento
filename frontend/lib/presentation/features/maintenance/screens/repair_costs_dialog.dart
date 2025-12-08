import 'package:flutter/material.dart';
import '../../../../data/models/reparacion_model.dart';
import '../widgets/repair_costs_widget.dart'; // Importa el widget que acabamos de crear

class RepairCostsDialog extends StatelessWidget {
  final ReparacionModel reparacion;

  const RepairCostsDialog({super.key, required this.reparacion});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SizedBox(
        width: 600, // Ancho cómodo para gestionar costes
        height: 700,
        child: Column(
          children: [
            // Cabecera
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  const Icon(Icons.euro, color: Colors.indigo, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Gestión de Costes", style: Theme.of(context).textTheme.titleLarge),
                        Text("Reparación #${reparacion.id} - ${reparacion.titulo}", 
                             style: const TextStyle(color: Colors.grey, fontSize: 12)),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  )
                ],
              ),
            ),
            const Divider(height: 1),
            // Cuerpo: Reutilizamos el widget de costes
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: RepairCostsWidget(reparacionId: reparacion.id),
              ),
            ),
          ],
        ),
      ),
    );
  }
}