import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';

enum Environment { dev, prod }

class EnvConfig {
  static const Environment currentEnv = Environment.dev;

  static String get apiUrl {
    if (currentEnv == Environment.prod) {
      return 'https://api.tu-produccion.com/api';
    }

    // Entorno Desarrollo
    if (kIsWeb) {
      return 'http://localhost:8000/api';
    }

    // Android Emulator (IP especial para ver el host)
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api';
    }

    // iOS Simulator / Windows Desktop
    return 'http://127.0.0.1:8000/api';
  }

  static const int connectTimeout = 5000;   // 5s
  static const int receiveTimeout = 10000;  // 10s
}