// frontend/lib/data/models/ubicacion_model.dart
class UbicacionModel {
  final int id;
  final String nombre;

  const UbicacionModel({
    required this.id,
    required this.nombre,
  });

  factory UbicacionModel.fromJson(Map<String, dynamic> json) {
    // Aseguramos que el id sea int aunque venga como String
    final dynamic rawId = json['id'];

    // Por si en backend algún día usan otro campo de texto
    final dynamic rawNombre =
        json['nombre'] ??
        json['descripcion'] ??
        json['nombre_ubicacion'] ??
        json['label'];

    return UbicacionModel(
      id: rawId is int ? rawId : int.parse(rawId.toString()),
      nombre: (rawNombre ?? '').toString(),
    );
  }
}
