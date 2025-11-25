import 'package:json_annotation/json_annotation.dart';

part 'reparacion_model.g.dart';

@JsonSerializable()
class ReparacionModel {
  final int id;
  @JsonKey(name: 'equipo_id')
  final int equipoId;
  
  @JsonKey(name: 'incidencia_id') // <--- NUEVO CAMPO
  final int? incidenciaId;

  final String titulo;
  final String? descripcion;
  final String estado; 
  
  @JsonKey(name: 'fecha_inicio')
  final String? fechaInicio;
  @JsonKey(name: 'fecha_fin')
  final String? fechaFin;
  
  final double? coste;

  const ReparacionModel({
    required this.id,
    required this.equipoId,
    this.incidenciaId, // <--- AÑADIR AL CONSTRUCTOR
    required this.titulo,
    this.descripcion,
    required this.estado,
    this.fechaInicio,
    this.fechaFin,
    this.coste,
  });

  factory ReparacionModel.fromJson(Map<String, dynamic> json) => _$ReparacionModelFromJson(json);
  Map<String, dynamic> toJson() => _$ReparacionModelToJson(this);
}