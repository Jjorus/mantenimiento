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
      costeMateriales: _parseCoste(json['coste_materiales']),
      costeManoObra: _parseCoste(json['coste_mano_obra']),
      costeOtros: _parseCoste(json['coste_otros']),
      moneda: json['moneda'] as String?,
      proveedor: json['proveedor'] as String?,
      numeroFactura: json['numero_factura'] as String?,
      facturaArchivoNombre: json['factura_archivo_nombre'] as String?,
      facturaArchivoPath: json['factura_archivo_path'] as String?,
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
      'coste_materiales': instance.costeMateriales,
      'coste_mano_obra': instance.costeManoObra,
      'coste_otros': instance.costeOtros,
      'moneda': instance.moneda,
      'proveedor': instance.proveedor,
      'numero_factura': instance.numeroFactura,
      'factura_archivo_nombre': instance.facturaArchivoNombre,
      'factura_archivo_path': instance.facturaArchivoPath,
    };
