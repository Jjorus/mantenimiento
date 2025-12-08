import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../data/models/gasto_model.dart';
import '../../../../data/repositories/maintenance_repository.dart';
import '../../../../logic/maintenance_cubit/maintenance_cubit.dart';

class RepairCostsWidget extends StatefulWidget {
  final int reparacionId;

  const RepairCostsWidget({super.key, required this.reparacionId});

  @override
  State<RepairCostsWidget> createState() => _RepairCostsWidgetState();
}

class _RepairCostsWidgetState extends State<RepairCostsWidget> {
  late Future<List<GastoModel>> _gastosFuture;
  final _costeDescController = TextEditingController();
  final _costeImporteController = TextEditingController();
  String _selectedTipoGasto = 'MATERIALES';
  bool _isAddingGasto = false;

  @override
  void initState() {
    super.initState();
    _refreshGastos();
  }

  @override
  void dispose() {
    _costeDescController.dispose();
    _costeImporteController.dispose();
    super.dispose();
  }

  void _refreshGastos() {
    setState(() {
      _gastosFuture = context.read<MaintenanceRepository>().listarGastos(widget.reparacionId);
    });
    // Actualizamos el dashboard global para que la tabla principal sume el total
    context.read<MaintenanceCubit>().loadDashboardData();
  }

  Future<void> _agregarGasto() async {
    final desc = _costeDescController.text.trim();
    final impText = _costeImporteController.text.trim().replaceAll(',', '.');
    final imp = double.tryParse(impText);

    if (desc.isEmpty || imp == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Datos incompletos"), backgroundColor: Colors.orange));
      return;
    }

    setState(() => _isAddingGasto = true);
    try {
      await context.read<MaintenanceRepository>().agregarGasto(
        widget.reparacionId, desc, imp, _selectedTipoGasto
      );
      if (!mounted) return;
      
      _costeDescController.clear();
      _costeImporteController.clear();
      _refreshGastos();
      
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Gasto añadido"), backgroundColor: Colors.green));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al añadir"), backgroundColor: Colors.red));
    } finally {
      if (mounted) setState(() => _isAddingGasto = false);
    }
  }

  Future<void> _borrarGasto(int id) async {
     try {
      await context.read<MaintenanceRepository>().eliminarGasto(widget.reparacionId, id);
      if (!mounted) return;
      _refreshGastos();
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Eliminado")));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al borrar"), backgroundColor: Colors.red));
    }
  }

  @override
  Widget build(BuildContext context) {
    // Detectamos si el tema es oscuro para ajustar colores manualmente si es necesario
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? Colors.white : Colors.black87;

    return Column(
      children: [
        // LISTA DE GASTOS
        Expanded(
          child: FutureBuilder<List<GastoModel>>(
            future: _gastosFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
              final lista = snapshot.data ?? [];
              
              if (lista.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.euro, size: 40, color: Colors.grey[300]),
                      const Text("Sin costes asignados", style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                );
              }
              
              final total = lista.fold<double>(0, (sum, item) => sum + item.importe);

              return Column(
                children: [
                  Expanded(
                    child: ListView.separated(
                      itemCount: lista.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final g = lista[index];
                        IconData icon;
                        Color color;
                        if (g.tipo == 'MATERIALES') { icon = Icons.inventory_2; color = Colors.orange; }
                        else if (g.tipo == 'MANO_OBRA') { icon = Icons.engineering; color = Colors.blue; }
                        else { icon = Icons.miscellaneous_services; color = Colors.purple; }

                        return ListTile(
                          dense: true,
                          leading: Tooltip(message: g.tipo, child: Icon(icon, color: color)),
                          title: Text(g.descripcion, style: const TextStyle(fontWeight: FontWeight.bold)),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text("${g.importe.toStringAsFixed(2)} €", style: const TextStyle(fontWeight: FontWeight.bold)),
                              IconButton(
                                icon: const Icon(Icons.delete_outline, color: Colors.red, size: 20),
                                onPressed: () => _borrarGasto(g.id!),
                              )
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  // TOTAL VISIBLE (Adaptativo)
                  Container(
                    padding: const EdgeInsets.all(12),
                    // Fondo suave: índigo muy claro en modo claro, gris oscuro en modo oscuro
                    color: isDark ? Colors.grey[800] : Colors.indigo[50], 
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          "TOTAL COSTES:", 
                          style: TextStyle(
                            fontWeight: FontWeight.bold, 
                            fontSize: 14, 
                            color: textColor // Se adapta al tema
                          )
                        ),
                        Text(
                          "${total.toStringAsFixed(2)} €", 
                          style: TextStyle(
                            fontWeight: FontWeight.bold, 
                            fontSize: 18, 
                            color: isDark ? Colors.lightBlueAccent : Colors.indigo // Color acento visible
                          )
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
        
        const Divider(height: 1),
        
        // FORMULARIO INFERIOR
        Container(
          padding: const EdgeInsets.all(8),
          // Usamos el color de tarjeta del tema (blanco en claro, gris oscuro en oscuro)
          color: Theme.of(context).cardColor, 
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: TextField(
                      controller: _costeDescController,
                      // Eliminamos estilos forzados, TextField hereda del tema correctamente
                      decoration: const InputDecoration(
                        labelText: "Concepto",
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 1,
                    child: TextField(
                      controller: _costeImporteController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: "Importe (€)",
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    // DESPLEGABLE ADAPTATIVO
                    child: DropdownButtonFormField<String>(
                      value: _selectedTipoGasto,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 12),
                      ),
                      // Estilo del texto seleccionado:
                      // Usamos el color principal del tema o blanco en oscuro para que resalte
                      style: TextStyle(
                        color: isDark ? Colors.white : Colors.indigo, 
                        fontWeight: FontWeight.bold, 
                        fontSize: 14
                      ),
                      // Color de fondo del menú desplegable (popup)
                      dropdownColor: Theme.of(context).cardColor, 
                      
                      // Items: Eliminamos el 'style' específico para que hereden el color del tema
                      // (negro en claro, blanco en oscuro) automáticamente.
                      items: const [
                        DropdownMenuItem(
                          value: 'MATERIALES', 
                          child: Text('Materiales') 
                        ),
                        DropdownMenuItem(
                          value: 'MANO_OBRA', 
                          child: Text('Mano de Obra')
                        ),
                        DropdownMenuItem(
                          value: 'OTROS', 
                          child: Text('Otros')
                        ),
                      ],
                      onChanged: (v) => setState(() => _selectedTipoGasto = v!),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.indigo,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                    ),
                    onPressed: _isAddingGasto ? null : _agregarGasto,
                    icon: _isAddingGasto 
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) 
                        : const Icon(Icons.add),
                    label: const Text("Añadir"),
                  ),
                ],
              )
            ],
          ),
        ),
      ],
    );
  }
}