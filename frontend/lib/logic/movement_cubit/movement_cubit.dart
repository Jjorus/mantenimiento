import 'dart:io' show Platform; // NUEVO: Para detectar si es Windows
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'package:nfc_manager/platform_tags.dart'; 

import '../../data/repositories/movement_repository.dart';
import '../../core/api/api_exception.dart';
import 'movement_state.dart';

class MovementCubit extends Cubit<MovementState> {
  final MovementRepository _repository;

  MovementCubit(this._repository) : super(const MovementState());

  Future<void> startNfcSession() async {
    // 1. PROTECCIÓN PLATAFORMA: Si no es móvil, abortamos antes de llamar al plugin
    // Esto evita el MissingPluginException en Windows
    if (!Platform.isAndroid && !Platform.isIOS) {
      emit(state.copyWith(
        status: MovementStatus.failure, 
        errorMessage: "NFC solo disponible en dispositivos móviles (Android/iOS)"
      ));
      return;
    }

    try {
      // 2. Comprobar disponibilidad (Ahora seguro porque sabemos que es móvil)
      bool isAvailable = await NfcManager.instance.isAvailable();
      if (!isAvailable) {
        emit(state.copyWith(
          status: MovementStatus.failure, 
          errorMessage: "NFC desactivado o no disponible"
        ));
        return;
      }
    } catch (_) {
       emit(state.copyWith(status: MovementStatus.failure, errorMessage: "Error verificando NFC"));
       return;
    }

    emit(state.copyWith(status: MovementStatus.scanning));

    // En v3.3.0 pollingOptions es opcional, pero si tu versión lo pide, aquí está
    NfcManager.instance.startSession(
      onDiscovered: (NfcTag tag) async {
        try {
          final String nfcId = _extractTagIdHighLevel(tag);

          await NfcManager.instance.stopSession();

          await retirarPorNfc(nfcId);

        } catch (e) {
          await NfcManager.instance.stopSession();
          if (!isClosed) {
            emit(state.copyWith(
              status: MovementStatus.failure, 
              errorMessage: "Error leyendo etiqueta NFC"
            ));
          }
        }
      },
    );
  }

  String _extractTagIdHighLevel(NfcTag tag) {
    List<int>? identifier;

    final isoDep = IsoDep.from(tag);
    if (isoDep != null) {
      identifier = isoDep.identifier;
    }
    else {
      final nfcA = NfcA.from(tag);
      if (nfcA != null) {
        identifier = nfcA.identifier;
      }
      else {
        final mifare = MifareClassic.from(tag);
        if (mifare != null) {
          identifier = mifare.identifier;
        }
        else {
            final nfcB = NfcB.from(tag);
            if (nfcB != null) {
                identifier = nfcB.identifier;
            }
            else {
                final nfcF = NfcF.from(tag);
                if (nfcF != null) {
                    identifier = nfcF.identifier;
                }
                else {
                    final nfcV = NfcV.from(tag);
                    if (nfcV != null) {
                        identifier = nfcV.identifier;
                    }
                }
            }
        }
      }
    }

    if (identifier == null) return "unknown_tag";

    return identifier.map((e) => e.toRadixString(16).padLeft(2, '0')).join().toUpperCase();
  }

  Future<void> retirarPorNfc(String tag, {String? comentario}) async {
    if (isClosed) return;
    emit(state.copyWith(status: MovementStatus.processing));
    
    try {
      final movimiento = await _repository.retirarPorNfc(tag, comentario: comentario);
      if (!isClosed) {
        emit(state.copyWith(
          status: MovementStatus.success,
          lastMovement: movimiento,
        ));
      }
    } on ApiException catch (e) {
      if (!isClosed) emit(state.copyWith(status: MovementStatus.failure, errorMessage: e.message));
    } catch (e) {
      if (!isClosed) emit(state.copyWith(status: MovementStatus.failure, errorMessage: "Error inesperado"));
    }
  }

  Future<void> retirarManual(int equipoId, {String? comentario}) async {
    if (isClosed) return;
    emit(state.copyWith(status: MovementStatus.processing));
    
    try {
      final movimiento = await _repository.retirarManual(equipoId, comentario: comentario);
      if (!isClosed) {
        emit(state.copyWith(
          status: MovementStatus.success,
          lastMovement: movimiento,
        ));
      }
    } on ApiException catch (e) {
      if (!isClosed) emit(state.copyWith(status: MovementStatus.failure, errorMessage: e.message));
    } catch (e) {
      if (!isClosed) emit(state.copyWith(status: MovementStatus.failure, errorMessage: "Error inesperado"));
    }
  }
  
  void reset() {
    if (!isClosed) emit(const MovementState());
  }
}