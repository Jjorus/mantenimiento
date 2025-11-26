import 'dart:io'; // <--- Importante importar dart:io para 'File'
import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs}) : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) => _remoteDs.getEquipoByNfc(tag);
  
  Future<List<EquipoModel>> buscarEquipos({String? query}) => 
      _remoteDs.getEquipos(query: query);

  // --- MÉTODOS NUEVOS (PASARELA) ---

  Future<void> subirAdjuntoEquipo(int id, File file) => 
      _remoteDs.uploadAdjuntoEquipo(id, file);

  // También te dejo estos listos por si los usas en la UI para ver/descargar
  Future<List<Map<String, String>>> listarAdjuntos(int id) =>
      _remoteDs.getAdjuntosEquipoURLs(id);

  Future<File> descargarArchivo(String url, String fileName) =>
      _remoteDs.downloadFile(url, fileName);
}