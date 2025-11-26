import 'dart:io';
import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs}) : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) => _remoteDs.getEquipoByNfc(tag);
  
  Future<List<EquipoModel>> buscarEquipos({String? query}) => 
      _remoteDs.getEquipos(query: query);

  // NUEVO: Notas
  Future<void> actualizarNotas(int id, String notas) =>
      _remoteDs.updateEquipo(id, notas: notas);

  // Adjuntos
  Future<void> subirAdjuntoEquipo(int id, File file) => 
      _remoteDs.uploadAdjuntoEquipo(id, file);

  Future<List<Map<String, String>>> listarAdjuntos(int id) =>
      _remoteDs.getAdjuntosEquipoURLs(id);

  Future<File> descargarArchivo(String url, String fileName) =>
      _remoteDs.downloadFile(url, fileName);

  // NUEVO: Borrar
  Future<void> eliminarAdjunto(int equipoId, int adjuntoId) =>
      _remoteDs.deleteAdjuntoEquipo(equipoId, adjuntoId);
}