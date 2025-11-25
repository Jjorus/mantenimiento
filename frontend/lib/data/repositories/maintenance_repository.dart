// Ruta: frontend/lib/data/repositories/maintenance_repository.dart
import 'dart:io';
import '../datasources/maintenance_remote_ds.dart';
import '../models/incidencia_model.dart';
import '../models/reparacion_model.dart';

class MaintenanceRepository {
  final MaintenanceRemoteDataSource _remoteDs;

  MaintenanceRepository({required MaintenanceRemoteDataSource remoteDs}) 
      : _remoteDs = remoteDs;

  // Incidencias
  Future<List<IncidenciaModel>> getIncidencias({int? equipoId, String? estado}) => 
      _remoteDs.getIncidencias(equipoId: equipoId, estado: estado);

  Future<void> reportarIncidencia(int equipoId, String titulo, String? descripcion) =>
      _remoteDs.createIncidencia(equipoId, titulo, descripcion);

  Future<void> cambiarEstadoIncidencia(int id, String nuevoEstado) =>
      _remoteDs.updateIncidenciaEstado(id, nuevoEstado);

  // Reparaciones
  Future<void> crearReparacion({
    required int equipoId,
    required int incidenciaId,
    required String titulo,
    String? descripcion,
    double? costeMateriales,
    double? costeManoObra,
  }) =>
      _remoteDs.createReparacion(
        equipoId: equipoId,
        incidenciaId: incidenciaId,
        titulo: titulo,
        descripcion: descripcion,
        costeMateriales: costeMateriales,
        costeManoObra: costeManoObra,
      );
  
  Future<List<ReparacionModel>> getReparaciones({int? equipoId}) => 
      _remoteDs.getReparaciones(equipoId: equipoId);

  // Archivos
  Future<void> subirFactura(int reparacionId, File file) => 
      _remoteDs.uploadFactura(reparacionId, file);

  Future<List<String>> listarFacturas(int reparacionId) => 
      _remoteDs.getFacturasURLs(reparacionId);

  Future<File> descargarArchivo(String url) => 
      _remoteDs.downloadFile(url);
}