class GastoModel {
  final int? id;
  final int reparacionId;
  final String descripcion;
  final double importe;
  final String tipo; // 'MATERIALES', 'MANO_OBRA', 'OTROS'

  GastoModel({
    this.id,
    required this.reparacionId,
    required this.descripcion,
    required this.importe,
    required this.tipo,
  });

  factory GastoModel.fromJson(Map<String, dynamic> json) {
    return GastoModel(
      id: json['id'],
      reparacionId: json['reparacion_id'],
      descripcion: json['descripcion'],
      importe: (json['importe'] as num).toDouble(),
      tipo: json['tipo'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'reparacion_id': reparacionId,
      'descripcion': descripcion,
      'importe': importe,
      'tipo': tipo,
    };
  }
}