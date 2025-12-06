// frontend/lib/data/models/ubicacion_model.dart
class UbicacionModel {
  final int id;
  final String nombre;

  const UbicacionModel({
    required this.id,
    required this.nombre,
  });

  factory UbicacionModel.fromJson(Map<String, dynamic> json) {
    return UbicacionModel(
      id: json['id'] as int,
      nombre: json['nombre'] as String,
    );
  }
}
