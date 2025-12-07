import 'dart:io';
import '../datasources/inventory_remote_ds.dart';
import '../models/equipo_model.dart';
import '../models/ubicacion_model.dart'; // <--- NUEVO

class InventoryRepository {
  final InventoryRemoteDataSource _remoteDs;

  InventoryRepository({required InventoryRemoteDataSource remoteDs})
      : _remoteDs = remoteDs;

  Future<EquipoModel> buscarPorNfc(String tag) =>
      _remoteDs.getEquipoByNfc(tag);

  Future<List<EquipoModel>> buscarEquipos({String? query}) =>
      _remoteDs.getEquipos(query: query);

  // Listar ubicaciones para poder obtener el nombre
  Future<List<UbicacionModel>> listarUbicaciones() =>
      _remoteDs.getUbicaciones();

    // Crear ubicación (wrapper de datasource)
  Future<UbicacionModel> crearUbicacion({
    required String nombre,
    int? seccionId,
    String tipo = 'OTRO',
    int? usuarioId,
  }) {
    return _remoteDs.crearUbicacion(
      nombre: nombre,
      seccionId: seccionId,
      tipo: tipo,
      usuarioId: usuarioId,
    );
  }
   

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
  }) =>
      _remoteDs.createEquipo(
        identidad: identidad,
        numeroSerie: numeroSerie,
        tipo: tipo,
        estado: estado,
        nfcTag: nfcTag,
        seccionId: seccionId,
        ubicacionId: ubicacionId,
        notas: notas,
      );

  // Actualizar equipo
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


  // Actualizar solo notas
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

  Future<void> eliminarEquipo(int id) => _remoteDs.deleteEquipo(id);

}
