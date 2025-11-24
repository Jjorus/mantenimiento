import 'dart:io';
import '../datasources/maintenance_remote_ds.dart';
import '../models/incidencia_model.dart';
import '../models/reparacion_model.dart';

class MaintenanceRepository {
  final MaintenanceRemoteDataSource _remoteDs;

  MaintenanceRepository({required MaintenanceRemoteDataSource remoteDs}) 
      : _remoteDs = remoteDs;

  // Incidencias
  Future<List<IncidenciaModel>> getIncidencias() => _remoteDs.getIncidencias();

  Future<void> reportarIncidencia(int equipoId, String titulo, String? descripcion) =>
      _remoteDs.createIncidencia(equipoId, titulo, descripcion);

  // Reparaciones
  Future<List<ReparacionModel>> getReparaciones() => _remoteDs.getReparaciones();

  // Archivos
  Future<void> subirFactura(int reparacionId, File file) => 
      _remoteDs.uploadFactura(reparacionId, file);

  Future<List<String>> listarFacturas(int reparacionId) => 
      _remoteDs.getFacturasURLs(reparacionId);

  Future<File> descargarArchivo(String url) => 
      _remoteDs.downloadFile(url);
}