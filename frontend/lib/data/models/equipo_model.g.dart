// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'equipo_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

EquipoModel _$EquipoModelFromJson(Map<String, dynamic> json) => EquipoModel(
  id: (json['id'] as num).toInt(),
  identidad: json['identidad'] as String?,
  numeroSerie: json['numero_serie'] as String?,
  tipo: json['tipo'] as String,
  estado: json['estado'] as String,
  nfcTag: json['nfc_tag'] as String?,
  ubicacionId: (json['ubicacion_id'] as num?)?.toInt(),
  seccionId: (json['seccion_id'] as num?)?.toInt(),
  creadoEn: json['creado_en'] as String?,
);

Map<String, dynamic> _$EquipoModelToJson(EquipoModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'identidad': instance.identidad,
      'numero_serie': instance.numeroSerie,
      'tipo': instance.tipo,
      'estado': instance.estado,
      'nfc_tag': instance.nfcTag,
      'ubicacion_id': instance.ubicacionId,
      'seccion_id': instance.seccionId,
      'creado_en': instance.creadoEn,
    };
