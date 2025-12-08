import 'package:json_annotation/json_annotation.dart';

part 'reparacion_model.g.dart';

// --- FUNCIÓN AUXILIAR PARA LEER NÚMEROS O TEXTOS ---
double? _parseCoste(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

@JsonSerializable()
class ReparacionModel {
  final int id;
  @JsonKey(name: 'equipo_id')
  final int equipoId;
  
  @JsonKey(name: 'incidencia_id')
  final int? incidenciaId;

  final String titulo;
  final String? descripcion;
  final String estado; 
  
  @JsonKey(name: 'fecha_inicio')
  final String? fechaInicio;
  @JsonKey(name: 'fecha_fin')
  final String? fechaFin;

  // --- COSTES (Con conversor seguro) ---
  @JsonKey(name: 'coste_materiales', fromJson: _parseCoste)
  final double? costeMateriales;

  @JsonKey(name: 'coste_mano_obra', fromJson: _parseCoste)
  final double? costeManoObra;

  @JsonKey(name: 'coste_otros', fromJson: _parseCoste)
  final double? costeOtros;

  // --- EXTRAS ---
  final String? moneda;
  final String? proveedor;
  @JsonKey(name: 'numero_factura')
  final String? numeroFactura;

  // Metadatos de factura principal
  @JsonKey(name: 'factura_archivo_nombre')
  final String? facturaArchivoNombre;
  @JsonKey(name: 'factura_archivo_path')
  final String? facturaArchivoPath;

  const ReparacionModel({
    required this.id,
    required this.equipoId,
    this.incidenciaId,
    required this.titulo,
    this.descripcion,
    required this.estado,
    this.fechaInicio,
    this.fechaFin,
    this.costeMateriales,
    this.costeManoObra,
    this.costeOtros,
    this.moneda,
    this.proveedor,
    this.numeroFactura,
    this.facturaArchivoNombre,
    this.facturaArchivoPath,
  });

  // --- GETTER INTELIGENTE (Suma automática) ---
  double get coste => (costeMateriales ?? 0) + (costeManoObra ?? 0) + (costeOtros ?? 0);

  factory ReparacionModel.fromJson(Map<String, dynamic> json) => _$ReparacionModelFromJson(json);
  Map<String, dynamic> toJson() => _$ReparacionModelToJson(this);
}