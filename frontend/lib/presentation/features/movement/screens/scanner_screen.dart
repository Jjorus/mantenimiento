import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/movement_cubit/movement_cubit.dart';
import '../../../../logic/movement_cubit/movement_state.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final _manualController = TextEditingController();
  final _commentController = TextEditingController();

  @override
  void dispose() {
    _manualController.dispose();
    _commentController.dispose();
    super.dispose();
  }

  void _onManualSubmit() {
    final id = int.tryParse(_manualController.text);
    if (id == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("ID inválido. Debe ser un número.")),
      );
      return;
    }
    // Ocultar teclado
    FocusScope.of(context).unfocus();
    
    final comentario = _commentController.text.trim();
    context.read<MovementCubit>().retirarManual(
      id, 
      comentario: comentario.isEmpty ? null : comentario
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<MovementCubit, MovementState>(
      listener: (context, state) {
        if (state.status == MovementStatus.success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text("¡Éxito! Equipo ${state.lastMovement?.equipoId} retirado."),
              backgroundColor: Colors.green,
            ),
          );
          // Limpieza para siguiente uso
          _manualController.clear();
          _commentController.clear();
          context.read<MovementCubit>().reset();
        }
        
        if (state.status == MovementStatus.failure) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(state.errorMessage ?? "Error"),
              backgroundColor: Colors.red,
            ),
          );
        }
      },
      builder: (context, state) {
        final isProcessing = state.status == MovementStatus.processing;
        final isScanning = state.status == MovementStatus.scanning;

        return Scaffold(
          appBar: AppBar(title: const Text("Retirar Equipo")),
          body: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // --- TARJETA NFC ---
                Expanded(
                  flex: 4,
                  child: Material(
                    color: isScanning 
                        ? Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3)
                        : Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(24),
                    child: InkWell(
                      onTap: (isProcessing || isScanning) 
                          ? null 
                          : () => context.read<MovementCubit>().startNfcSession(),
                      borderRadius: BorderRadius.circular(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            isScanning ? Icons.wifi_tethering : Icons.nfc,
                            size: 80,
                            color: isScanning 
                                ? Theme.of(context).colorScheme.primary 
                                : Colors.grey,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            isScanning ? "Acerca el equipo..." : "Tocar para Escanear NFC",
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          if (isScanning)
                            const Padding(
                              padding: EdgeInsets.only(top: 24.0),
                              child: CircularProgressIndicator(),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
                
                const SizedBox(height: 24),
                const Divider(height: 1),
                const SizedBox(height: 24),

                // --- ENTRADA MANUAL ---
                Expanded(
                  flex: 6,
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Entrada Manual", style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _manualController,
                                keyboardType: TextInputType.number,
                                decoration: const InputDecoration(
                                  labelText: "ID Equipo",
                                  prefixIcon: Icon(Icons.tag),
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),
                            FloatingActionButton(
                              onPressed: isProcessing ? null : _onManualSubmit,
                              elevation: 0,
                              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                              child: isProcessing 
                                  ? const Padding(
                                      padding: EdgeInsets.all(12.0),
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.arrow_forward),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _commentController,
                          decoration: const InputDecoration(
                            labelText: "Comentario (Opcional)",
                            prefixIcon: Icon(Icons.comment_outlined),
                            border: OutlineInputBorder(),
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
      },
    );
  }
}