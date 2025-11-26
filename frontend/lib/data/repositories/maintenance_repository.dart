// Ruta: frontend/lib/data/repositories/maintenance_repository.dart
import 'dart:io';
import '../datasources/maintenance_remote_ds.dart';
import '../models/incidencia_model.dart';
import '../models/reparacion_model.dart';

class MaintenanceRepository {
  final MaintenanceRemoteDataSource _remoteDs;

  MaintenanceRepository({required MaintenanceRemoteDataSource remoteDs}) 
      : _remoteDs = remoteDs;

  // --- INCIDENCIAS ---
  Future<List<IncidenciaModel>> getIncidencias({int? equipoId, String? estado}) => 
      _remoteDs.getIncidencias(equipoId: equipoId, estado: estado);

  Future<void> reportarIncidencia(int equipoId, String titulo, String? descripcion) =>
      _remoteDs.createIncidencia(equipoId, titulo, descripcion);

  Future<void> cambiarEstadoIncidencia(int id, String nuevoEstado) =>
      _remoteDs.updateIncidenciaEstado(id, nuevoEstado);

  Future<void> actualizarIncidencia(int id, {String? descripcion}) =>
      _remoteDs.updateIncidencia(id, descripcion: descripcion);

  Future<void> subirAdjuntoIncidencia(int incidenciaId, File file) =>
      _remoteDs.uploadAdjuntoIncidencia(incidenciaId, file);

  // Devuelve lista de objetos {url, fileName}
  Future<List<Map<String, String>>> listarAdjuntosIncidencia(int incidenciaId) =>
      _remoteDs.getAdjuntosIncidenciaURLs(incidenciaId);


  // --- REPARACIONES ---
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

  Future<void> actualizarReparacion(int id, {String? descripcion}) =>
      _remoteDs.updateReparacion(id, descripcion: descripcion);

  Future<void> subirFactura(int reparacionId, File file) => 
      _remoteDs.subirFactura(reparacionId, file);

  // Devuelve lista de objetos {url, fileName}
  Future<List<Map<String, String>>> listarFacturas(int reparacionId) => 
      _remoteDs.getFacturasURLs(reparacionId);

  // Acepta fileName
  Future<File> descargarArchivo(String url, String fileName) => 
      _remoteDs.downloadFile(url, fileName);
}