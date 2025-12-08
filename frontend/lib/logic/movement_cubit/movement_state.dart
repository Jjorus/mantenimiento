import 'package:equatable/equatable.dart';
import '../../data/models/movimiento_model.dart';

enum MovementStatus { 
  initial,      // Esperando acción
  scanning,     // Leyendo NFC (spinner / animación)
  processing,   // Enviando al backend
  success,      // Movimiento completado OK
  failure       // Error (API o NFC)
}

class MovementState extends Equatable {
  final MovementStatus status;
  final MovimientoModel? lastMovement; // Para mostrar feedback "Equipo X retirado"
  final String? errorMessage;

  const MovementState({
    this.status = MovementStatus.initial,
    this.lastMovement,
    this.errorMessage,
  });

  MovementState copyWith({
    MovementStatus? status,
    MovimientoModel? lastMovement,
    String? errorMessage,
  }) {
    return MovementState(
      status: status ?? this.status,
      lastMovement: lastMovement ?? this.lastMovement,
      // Si pasamos null explícitamente, limpiamos el error anterior
      errorMessage: errorMessage, 
    );
  }

  @override
  List<Object?> get props => [status, lastMovement, errorMessage];
}