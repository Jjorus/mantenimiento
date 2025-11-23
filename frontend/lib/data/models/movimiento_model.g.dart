// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'movimiento_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

MovimientoModel _$MovimientoModelFromJson(Map<String, dynamic> json) =>
    MovimientoModel(
      id: (json['id'] as num).toInt(),
      equipoId: (json['equipo_id'] as num).toInt(),
      haciaUbicacionId: (json['hacia_ubicacion_id'] as num?)?.toInt(),
      usuarioId: (json['usuario_id'] as num?)?.toInt(),
      comentario: json['comentario'] as String?,
      fecha: json['fecha'] as String?,
    );

Map<String, dynamic> _$MovimientoModelToJson(MovimientoModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'equipo_id': instance.equipoId,
      'hacia_ubicacion_id': instance.haciaUbicacionId,
      'usuario_id': instance.usuarioId,
      'comentario': instance.comentario,
      'fecha': instance.fecha,
    };
