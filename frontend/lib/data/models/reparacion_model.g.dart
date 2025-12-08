// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'reparacion_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ReparacionModel _$ReparacionModelFromJson(Map<String, dynamic> json) =>
    ReparacionModel(
      id: (json['id'] as num).toInt(),
      equipoId: (json['equipo_id'] as num).toInt(),
      incidenciaId: (json['incidencia_id'] as num?)?.toInt(),
      titulo: json['titulo'] as String,
      descripcion: json['descripcion'] as String?,
      estado: json['estado'] as String,
      fechaInicio: json['fecha_inicio'] as String?,
      fechaFin: json['fecha_fin'] as String?,
      coste: (json['coste'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$ReparacionModelToJson(ReparacionModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'equipo_id': instance.equipoId,
      'incidencia_id': instance.incidenciaId,
      'titulo': instance.titulo,
      'descripcion': instance.descripcion,
      'estado': instance.estado,
      'fecha_inicio': instance.fechaInicio,
      'fecha_fin': instance.fechaFin,
      'coste': instance.coste,
    };
