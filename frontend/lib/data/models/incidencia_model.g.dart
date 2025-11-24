// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'incidencia_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

IncidenciaModel _$IncidenciaModelFromJson(Map<String, dynamic> json) =>
    IncidenciaModel(
      id: (json['id'] as num).toInt(),
      equipoId: (json['equipo_id'] as num).toInt(),
      titulo: json['titulo'] as String,
      descripcion: json['descripcion'] as String?,
      estado: json['estado'] as String,
      fecha: json['fecha'] as String?,
    );

Map<String, dynamic> _$IncidenciaModelToJson(IncidenciaModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'equipo_id': instance.equipoId,
      'titulo': instance.titulo,
      'descripcion': instance.descripcion,
      'estado': instance.estado,
      'fecha': instance.fecha,
    };
