import 'package:json_annotation/json_annotation.dart';

part 'incidencia_model.g.dart';

@JsonSerializable()
class IncidenciaModel {
  final int id;
  @JsonKey(name: 'equipo_id')
  final int equipoId;
  final String titulo;
  final String? descripcion;
  final String estado; // ABIERTA, EN_PROGRESO, CERRADA
  final String? fecha;

  const IncidenciaModel({
    required this.id,
    required this.equipoId,
    required this.titulo,
    this.descripcion,
    required this.estado,
    this.fecha,
  });

  factory IncidenciaModel.fromJson(Map<String, dynamic> json) => _$IncidenciaModelFromJson(json);
  Map<String, dynamic> toJson() => _$IncidenciaModelToJson(this);
}