import 'dart:io';
import '../datasources/maintenance_remote_ds.dart';
import '../models/incidencia_model.dart';
import '../models/reparacion_model.dart';
import '../models/gasto_model.dart';

class MaintenanceRepository {
  final MaintenanceRemoteDataSource _remoteDs;

  MaintenanceRepository({required MaintenanceRemoteDataSource remoteDs})
      : _remoteDs = remoteDs;

  // --- INCIDENCIAS ---

  Future<List<IncidenciaModel>> getIncidencias({
    int? equipoId,
    String? estado,
  }) =>
      _remoteDs.getIncidencias(
        equipoId: equipoId,
        estado: estado,
      );

  Future<void> reportarIncidencia(
          int equipoId, String titulo, String? descripcion) =>
      _remoteDs.createIncidencia(
        equipoId: equipoId,
        titulo: titulo,
        descripcion: descripcion,
      );

  /// Cambiar solo el estado de la incidencia (ABIERTA / EN_PROGRESO / CERRADA)
  Future<void> cambiarEstadoIncidencia(int id, String nuevoEstado) =>
      _remoteDs.updateIncidencia(
        id,
        estado: nuevoEstado,
      );

  /// Actualizar solo la descripción de la incidencia
  Future<void> actualizarIncidencia(int id, {String? descripcion}) =>
      _remoteDs.updateIncidencia(
        id,
        descripcion: descripcion,
      );

  // --- Adjuntos de incidencias ---

  Future<void> subirAdjuntoIncidencia(int incidenciaId, File file) =>
      _remoteDs.uploadAdjuntoIncidencia(incidenciaId, file);

  Future<List<Map<String, dynamic>>> listarAdjuntosIncidencia(
          int incidenciaId) =>
      _remoteDs.getAdjuntosIncidenciaURLs(incidenciaId);

  Future<void> eliminarAdjuntoIncidencia(
          int incidenciaId, int adjuntoId) =>
      _remoteDs.deleteAdjuntoIncidencia(incidenciaId, adjuntoId);

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

  /// Ahora permite actualizar descripción y/o estado de la reparación
  Future<void> actualizarReparacion(
    int id, {
    String? descripcion,
    String? estado,
  }) =>
      _remoteDs.updateReparacion(
        id,
        descripcion: descripcion,
        estado: estado,
      );

  Future<void> cerrarReparacion(int id) => _remoteDs.closeReparacion(id);

  Future<void> reabrirReparacion(int id) => _remoteDs.reopenReparacion(id);

  // --- FACTURAS DE REPARACIÓN ---

  Future<void> subirFactura(int reparacionId, File file) =>
      _remoteDs.subirFactura(reparacionId, file);

  Future<List<Map<String, dynamic>>> listarFacturas(int reparacionId) =>
      _remoteDs.getFacturasURLs(reparacionId);

  Future<void> eliminarFactura(int reparacionId, int facturaId) =>
      _remoteDs.deleteFacturaReparacion(reparacionId, facturaId);

  // --- COMÚN ---

  Future<File> descargarArchivo(String url, String fileName) =>
      _remoteDs.downloadFile(url, fileName);

  // --- GASTOS ---

  Future<List<GastoModel>> listarGastos(int reparacionId) =>
      _remoteDs.getGastos(reparacionId);

  Future<void> agregarGasto(int reparacionId, String desc, double importe, String tipo) =>
      _remoteDs.addGasto(reparacionId, desc, importe, tipo);

  Future<void> eliminarGasto(int reparacionId, int gastoId) =>
      _remoteDs.deleteGasto(reparacionId, gastoId);
}
