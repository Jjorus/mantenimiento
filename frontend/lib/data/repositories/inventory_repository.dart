import 'dart:io';
import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs})
      : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) =>
      _remoteDs.getEquipoByNfc(tag);

  Future<List<EquipoModel>> buscarEquipos({String? query}) =>
      _remoteDs.getEquipos(query: query);

  // Crear equipo
  Future<void> crearEquipo({
    required String identidad,
    String? numeroSerie,
    required String tipo,
    String estado = 'OPERATIVO',
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) {
    final data = <String, dynamic>{
      'identidad': identidad,
      'tipo': tipo,
      'estado': estado,
      if (numeroSerie != null && numeroSerie.isNotEmpty)
        'numero_serie': numeroSerie,
      if (nfcTag != null && nfcTag.isNotEmpty) 'nfc_tag': nfcTag,
      if (seccionId != null) 'seccion_id': seccionId,
      if (ubicacionId != null) 'ubicacion_id': ubicacionId,
      if (notas != null && notas.isNotEmpty) 'notas': notas,
    };
    return _remoteDs.createEquipo(data);
  }

  // Actualizar ficha de equipo
  Future<void> actualizarEquipo({
    required int id,
    String? identidad,
    String? numeroSerie,
    String? tipo,
    String? estado,
    String? nfcTag,
    int? seccionId,
    int? ubicacionId,
    String? notas,
  }) {
    return _remoteDs.updateEquipo(
      id,
      identidad: identidad,
      numeroSerie: numeroSerie,
      tipo: tipo,
      estado: estado,
      nfcTag: nfcTag,
      seccionId: seccionId,
      ubicacionId: ubicacionId,
      notas: notas,
    );
  }

  // Atajo para notas
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
