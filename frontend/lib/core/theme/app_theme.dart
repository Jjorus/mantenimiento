import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryBlue = Color(0xFF0056B3);
  // ... otros colores ...

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryBlue, 
        brightness: Brightness.light
      ),
      scaffoldBackgroundColor: const Color(0xFFF8F9FA),
      
      // IMPORTANTE: Usar Typography.material2021() en lugar de GoogleFonts
      typography: Typography.material2021(),
      
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        // Aseguramos color de texto visible
        labelStyle: const TextStyle(color: Colors.black87),
        hintStyle: const TextStyle(color: Colors.black38),
      ),
    );
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryBlue, 
        brightness: Brightness.dark
      ),
      scaffoldBackgroundColor: const Color(0xFF121212),
      
      // IMPORTANTE: Typography nativa
      typography: Typography.material2021(platform: TargetPlatform.android),
      
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF1E1E1E),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        labelStyle: const TextStyle(color: Colors.white70),
        hintStyle: const TextStyle(color: Colors.white38),
      ),
    );
  }
}