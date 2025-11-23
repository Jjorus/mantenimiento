import 'package:json_annotation/json_annotation.dart';

part 'movimiento_model.g.dart';

@JsonSerializable()
class MovimientoModel {
  final int id;
  
  @JsonKey(name: 'equipo_id')
  final int equipoId;
  
  @JsonKey(name: 'hacia_ubicacion_id')
  final int? haciaUbicacionId;
  
  @JsonKey(name: 'usuario_id')
  final int? usuarioId; // Útil para saber quién hizo el movimiento

  final String? comentario;
  final String? fecha; // Coincide con backend

  const MovimientoModel({
    required this.id,
    required this.equipoId,
    this.haciaUbicacionId,
    this.usuarioId,
    this.comentario,
    this.fecha,
  });

  factory MovimientoModel.fromJson(Map<String, dynamic> json) => _$MovimientoModelFromJson(json);
  Map<String, dynamic> toJson() => _$MovimientoModelToJson(this);
}