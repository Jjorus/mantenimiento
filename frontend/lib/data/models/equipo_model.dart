import 'package:json_annotation/json_annotation.dart';

part 'equipo_model.g.dart';

@JsonSerializable()
class EquipoModel {
  final int id;
  final String? identidad;
  
  @JsonKey(name: 'numero_serie')
  final String? numeroSerie;
  
  final String tipo;
  final String estado; // OPERATIVO, MANTENIMIENTO...
  
  @JsonKey(name: 'nfc_tag')
  final String? nfcTag;
  
  @JsonKey(name: 'ubicacion_id')
  final int? ubicacionId;

  @JsonKey(name: 'seccion_id')
  final int? seccionId;

  @JsonKey(name: 'creado_en')
  final String? creadoEn;

  const EquipoModel({
    required this.id,
    this.identidad,
    this.numeroSerie,
    required this.tipo,
    required this.estado,
    this.nfcTag,
    this.ubicacionId,
    this.seccionId,
    this.creadoEn,
  });

  factory EquipoModel.fromJson(Map<String, dynamic> json) => _$EquipoModelFromJson(json);
  Map<String, dynamic> toJson() => _$EquipoModelToJson(this);
}