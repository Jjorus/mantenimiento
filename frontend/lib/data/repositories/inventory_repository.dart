import 'dart:io';
import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs}) : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) => _remoteDs.getEquipoByNfc(tag);
  
  Future<List<EquipoModel>> buscarEquipos({String? query}) => 
      _remoteDs.getEquipos(query: query);

  // --- NUEVO: Crear Equipo ---
  Future<void> crearEquipo({
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String estado = 'OPERATIVO',
    String? notas,
  }) {
    final data = {
      'identidad': identidad,
      'numero_serie': numeroSerie,
      'tipo': tipo,
      'estado': estado,
      'notas': notas,
    };
    return _remoteDs.createEquipo(data);
  }

  Future<void> actualizarNotas(int id, String notas) =>
      _remoteDs.updateEquipo(id, notas: notas);

  // Adjuntos
  Future<void> subirAdjuntoEquipo(int id, File file) => 
      _remoteDs.uploadAdjuntoEquipo(id, file);

  Future<List<Map<String, String>>> listarAdjuntos(int id) =>
      _remoteDs.getAdjuntosEquipoURLs(id);

  Future<File> descargarArchivo(String url, String fileName) =>
      _remoteDs.downloadFile(url, fileName);

  Future<void> eliminarAdjunto(int equipoId, int adjuntoId) =>
      _remoteDs.deleteAdjuntoEquipo(equipoId, adjuntoId);
}